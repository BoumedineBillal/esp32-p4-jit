// math_ops.cpp - C++ implementation for testing C++ compilation

typedef int int32_t;

// Use extern "C" to prevent name mangling for C linkage
extern "C" {
    int32_t vector_dot_product(int32_t x1, int32_t y1, int32_t x2, int32_t y2);
}

// Simple C++ class to test C++ features
class Vector {
private:
    int32_t x, y;

public:
    Vector(int32_t x_val, int32_t y_val) : x(x_val), y(y_val) {}
    
    int32_t dot(const Vector& other) const {
        return x * other.x + y * other.y;
    }
};

int32_t vector_dot_product(int32_t x1, int32_t y1, int32_t x2, int32_t y2) {
    Vector v1(x1, y1);
    Vector v2(x2, y2);
    return v1.dot(v2);
}
