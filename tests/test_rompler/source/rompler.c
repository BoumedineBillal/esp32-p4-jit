#include <stdint.h>
#include <math.h>
#include <string.h>


#define PI_2    1.5707963267948966192313216916398f
#define PI      3.1415926535897932384626433832795f
#define TWO_PI  6.283185307179586476925286766559f
#define PI_4    0.78539816339744830961566084581988f
#define FOUR_OVER_PI    1.2732395447351626861510701069801f


static inline uint32_t rdcycle(void) {
    uint32_t cycles;
    asm volatile ("rdcycle %0" : "=r"(cycles));
    return cycles;
}


// ==========================================
// 1. SELF-CONTAINED DSP IMPLEMENTATIONS
// ==========================================

// Standard biquad implementation
void dsps_biquad_f32(const float *input, float *output, int len, float *coef, float *w) {
    for (int i = 0; i < len; i++) {
        float d0 = input[i] - coef[3] * w[0] - coef[4] * w[1];
        output[i] = coef[0] * d0 + coef[1] * w[0] + coef[2] * w[1];
        w[1] = w[0];
        w[0] = d0;
    }
}


float cos_73(float x) {
#define COS_C1 0.999999953464f
#define COS_C2 -0.4999999053455f
#define COS_C3 0.0416635846769f
#define COS_C4 -0.0013853704264f
#define COS_C5 0.00002315393167f
    float x2 = x * x;
    return (COS_C1 + x2 * (COS_C2 + x2 * (COS_C3 + x2 * (COS_C4 + COS_C5 * x2))));
}

float fastcos(float x) {
    if (x < 0)x = -x;
    int quadrant = (int) (x / PI_2);
    switch (quadrant) {
        case 0:
            return cos_73(x);
        case 1:
            return -cos_73(PI - x);
        case 2:
            return -cos_73(x - PI);
        case 3:
            return cos_73(TWO_PI - x);
    }
    return 0.f;
}

float fastsin(float x) {
    return fastcos(PI_2 - x);
}

// Coefficient generator
void dsps_biquad_gen_lpf_f32(float *coeffs, float f, float qFactor) {
    if (qFactor <= 0.0001f) {
        qFactor = 0.0001f;
    }
    float Fs = 1.f; // Normalized frequency

    float w0 = 2.f * PI * f / Fs;
    float c = fastcos(w0);
    float s = fastsin(w0);
    float alpha = s / (2.f * qFactor);

    float b0 = (1.f - c) / 2.f;
    float b1 = 1.f - c;
    float b2 = b0;
    float a0 = 1.f + alpha;
    float a1 = -2.f * c;
    float a2 = 1.f - alpha;

    coeffs[0] = b0 / a0;
    coeffs[1] = b1 / a0;
    coeffs[2] = b2 / a0;
    coeffs[3] = a1 / a0;
    coeffs[4] = a2 / a0;
}

// ==========================================
// 2. THE ISOLATED BLOCK FUNCTION
// ==========================================

enum BufferStatus { STOPPED = 0, READFIRST = 1, READLAST = 2, RUNNING = 3 };

/**
 * The extracted logic from RomplerVoice::processBlock.
 * This processes exactly ONE chunk of data.
 */
void Rompler_ProcessOneBlock(float *readBufferFloat, 
                             int bufferStatus, 
                             float phaseIncrement, 
                             uint32_t readBufferLength,
                             float *coeffs_lpf,
                             float *w_lpf1,
                             float *w_lpf2,
                             float *w_lpf3) 
{
    // 1. Fade first incoming buffer
    // Expects readBufferFloat[4] to be the start of actual data
    if (bufferStatus == READFIRST) {
        readBufferFloat[0] = 0.001f * readBufferFloat[4];
        readBufferFloat[1] = 0.01f  * readBufferFloat[4];
        readBufferFloat[2] = 0.1f   * readBufferFloat[4];
        readBufferFloat[3] = 0.5f   * readBufferFloat[4];
    }

    // 2. Apply anti-aliasing low-pass
    float fAntiAlias = 0.5f / phaseIncrement;
    if (fAntiAlias < 0.5f) {
        // Calculate coeffs
        dsps_biquad_gen_lpf_f32(coeffs_lpf, fAntiAlias, .5f);
        
        // Apply 3 cascades
        dsps_biquad_f32(&readBufferFloat[4], &readBufferFloat[4], readBufferLength, coeffs_lpf, w_lpf1);
        dsps_biquad_f32(&readBufferFloat[4], &readBufferFloat[4], readBufferLength, coeffs_lpf, w_lpf2);
        dsps_biquad_f32(&readBufferFloat[4], &readBufferFloat[4], readBufferLength, coeffs_lpf, w_lpf3);
    }
}

// ==========================================
// 3. THE PARENT FUNCTION (Simulator)
// ==========================================

/**
 * Simulates the block-by-block processing on a large buffer.
 * 
 * @param largeAudioBuffer Pointer to the FULL audio data (Must have 4 floats padding at start).
 * @param totalSamples     Total size of the buffer (including padding).
 * @param phaseIncrement   Playback pitch.
 * @param coeffs_lpf       External array of 5 floats.
 * @param w_lpf1           External array of 2 floats (state).
 * @param w_lpf2           External array of 2 floats (state).
 * @param w_lpf3           External array of 2 floats (state).
 */
uint32_t Rompler_ApplyToLargeBuffer(float* largeAudioBuffer, 
                                uint32_t totalSamples, 
                                float phaseIncrement,
                                float* coeffs_lpf,
                                float* w_lpf1,
                                float* w_lpf2,
                                float* w_lpf3) 
{
    // Internal variables to simulate the exact length calculations
    float readBufferPhase = 0.0f;
    const uint32_t outputBlockSize = 32; // Fixed project constant
    
    // Start reading at index 4 (0-3 are padding/history)
    uint32_t currentReadPos = 4; 
    
    int currentStatus = READFIRST;
    
    uint32_t start = rdcycle();

    // Loop until we reach the end of the buffer
    while (currentReadPos < totalSamples) {
        
        // A. Calculate required length for this block (Matches RomplerVoice logic)
        uint32_t readBufferLength = (uint32_t)(phaseIncrement * (float)outputBlockSize + readBufferPhase);

        // B. Update phase remainder
        float totalPhase = phaseIncrement * (float)outputBlockSize + readBufferPhase;
        readBufferPhase = totalPhase - (float)readBufferLength; // Phase remainder

        // C. Boundary Check
        if (currentReadPos + readBufferLength > totalSamples) {
             readBufferLength = totalSamples - currentReadPos;
        }

        if (readBufferLength == 0) break;

        // D. Setup Pointer to Context
        // We point 4 samples *back* so the function can access [0]..[3] as history
        // and [4] as the new data start.
        float* currentBlockPtr = &largeAudioBuffer[currentReadPos - 4];

        // E. Call the Isolated Block Processor
        Rompler_ProcessOneBlock(
            currentBlockPtr, 
            currentStatus, 
            phaseIncrement, 
            readBufferLength, 
            coeffs_lpf, 
            w_lpf1, 
            w_lpf2, 
            w_lpf3
        );

        // F. Advance
        currentReadPos += readBufferLength;
        
        // After first block, status changes
        if (currentStatus == READFIRST) {
            currentStatus = RUNNING;
        }
    }
    
    uint32_t end = rdcycle();
    
    return end - start;
}



// ==========================================
// ASM FUNCTION DECLARATION
// ==========================================

// External assembly implementation of fused 3-cascade biquad
extern void dsps_biquad_f32_cascade3_arp4(float* inout, 
                                          int len, 
                                          float* coef, 
                                          float* w1, 
                                          float* w2, 
                                          float* w3);

// ==========================================
// MODIFIED BLOCK FUNCTION
// ==========================================

void Rompler_ProcessBlock2(float *readBufferFloat, 
                         int bufferStatus, 
                         float phaseIncrement, 
                         uint32_t readBufferLength,
                         float *coeffs_lpf,
                         float *w_lpf1,
                         float *w_lpf2,
                         float *w_lpf3) 
{
    if (bufferStatus == READFIRST) {
        readBufferFloat[0] = 0.001f * readBufferFloat[4];
        readBufferFloat[1] = 0.01f  * readBufferFloat[4];
        readBufferFloat[2] = 0.1f   * readBufferFloat[4];
        readBufferFloat[3] = 0.5f   * readBufferFloat[4];
    }

    float fAntiAlias = 0.5f / phaseIncrement;
    if (fAntiAlias < 0.5f) {
        dsps_biquad_gen_lpf_f32(coeffs_lpf, fAntiAlias, .5f);
        
        // Use fused assembly implementation
        dsps_biquad_f32_cascade3_arp4(&readBufferFloat[4], 
                                       readBufferLength, 
                                       coeffs_lpf, 
                                       w_lpf1, 
                                       w_lpf2, 
                                       w_lpf3);
    }
}

// ==========================================
// MODIFIED PARENT FUNCTION
// ==========================================

uint32_t Rompler_ApplyToLargeBuffer2(float* largeAudioBuffer, 
                                    uint32_t totalSamples, 
                                    float phaseIncrement,
                                    float* coeffs_lpf,
                                    float* w_lpf1,
                                    float* w_lpf2,
                                    float* w_lpf3) 
{
    float readBufferPhase = 0.0f;
    const uint32_t outputBlockSize = 32;
    uint32_t currentReadPos = 4; 
    int currentStatus = READFIRST;
    
    uint32_t start = rdcycle();

    while (currentReadPos < totalSamples) {
        uint32_t readBufferLength = (uint32_t)(phaseIncrement * (float)outputBlockSize + readBufferPhase);
        float totalPhase = phaseIncrement * (float)outputBlockSize + readBufferPhase;
        readBufferPhase = totalPhase - (float)readBufferLength;

        if (currentReadPos + readBufferLength > totalSamples) {
             readBufferLength = totalSamples - currentReadPos;
        }

        if (readBufferLength == 0) break;

        float* currentBlockPtr = &largeAudioBuffer[currentReadPos - 4];

        Rompler_ProcessBlock2(
            currentBlockPtr, 
            currentStatus, 
            phaseIncrement, 
            readBufferLength, 
            coeffs_lpf, 
            w_lpf1, 
            w_lpf2, 
            w_lpf3
        );

        currentReadPos += readBufferLength;
        
        if (currentStatus == READFIRST) {
            currentStatus = RUNNING;
        }
    }
    
    uint32_t end = rdcycle();
    return end - start;
}

// ==========================================
// ASM SINGLE BIQUAD DECLARATION
// ==========================================

extern void dsps_biquad_f32_arp4(const float *input, float *output, int len, float *coef, float *w);

// ==========================================
// SINGLE BIQUAD BLOCK FUNCTION
// ==========================================

void Rompler_ProcessBlock3(float *readBufferFloat, 
                         int bufferStatus, 
                         float phaseIncrement, 
                         uint32_t readBufferLength,
                         float *coeffs_lpf,
                         float *w_lpf1,
                         float *w_lpf2,
                         float *w_lpf3) 
{
    if (bufferStatus == READFIRST) {
        readBufferFloat[0] = 0.001f * readBufferFloat[4];
        readBufferFloat[1] = 0.01f  * readBufferFloat[4];
        readBufferFloat[2] = 0.1f   * readBufferFloat[4];
        readBufferFloat[3] = 0.5f   * readBufferFloat[4];
    }

    float fAntiAlias = 0.5f / phaseIncrement;
    if (fAntiAlias < 0.5f) {
        dsps_biquad_gen_lpf_f32(coeffs_lpf, fAntiAlias, .5f);
        
        // Use single biquad assembly implementation (Cascaded 3 times)
        dsps_biquad_f32_arp4(&readBufferFloat[4], &readBufferFloat[4], readBufferLength, coeffs_lpf, w_lpf1);
        dsps_biquad_f32_arp4(&readBufferFloat[4], &readBufferFloat[4], readBufferLength, coeffs_lpf, w_lpf2);
        dsps_biquad_f32_arp4(&readBufferFloat[4], &readBufferFloat[4], readBufferLength, coeffs_lpf, w_lpf3);
    }
}

// ==========================================
// SINGLE BIQUAD PARENT FUNCTION
// ==========================================

uint32_t Rompler_ApplyToLargeBuffer3(float* largeAudioBuffer, 
                                    uint32_t totalSamples, 
                                    float phaseIncrement,
                                    float* coeffs_lpf,
                                    float* w_lpf1,
                                    float* w_lpf2,
                                    float* w_lpf3) 
{
    float readBufferPhase = 0.0f;
    const uint32_t outputBlockSize = 32;
    uint32_t currentReadPos = 4; 
    int currentStatus = READFIRST;
    
    uint32_t start = rdcycle();

    while (currentReadPos < totalSamples) {
        uint32_t readBufferLength = (uint32_t)(phaseIncrement * (float)outputBlockSize + readBufferPhase);
        float totalPhase = phaseIncrement * (float)outputBlockSize + readBufferPhase;
        readBufferPhase = totalPhase - (float)readBufferLength;

        if (currentReadPos + readBufferLength > totalSamples) {
             readBufferLength = totalSamples - currentReadPos;
        }

        if (readBufferLength == 0) break;

        float* currentBlockPtr = &largeAudioBuffer[currentReadPos - 4];

        Rompler_ProcessBlock3(
            currentBlockPtr, 
            currentStatus, 
            phaseIncrement, 
            readBufferLength, 
            coeffs_lpf, 
            w_lpf1, 
            w_lpf2, 
            w_lpf3
        );

        currentReadPos += readBufferLength;
        
        if (currentStatus == READFIRST) {
            currentStatus = RUNNING;
        }
    }
    
    uint32_t end = rdcycle();
    return end - start;
}