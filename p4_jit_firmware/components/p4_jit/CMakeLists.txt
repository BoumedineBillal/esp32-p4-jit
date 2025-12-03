idf_component_register(SRCS "src/p4_jit.c"
                             "src/commands.c"
                             "src/protocol.c"
                             "src/usb_transport.c"
                       INCLUDE_DIRS "include" "src"
                       REQUIRES esp_timer driver esp_rom esp_mm heap log)
