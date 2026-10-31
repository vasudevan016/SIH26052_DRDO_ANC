idf_component_register(SRCS "main.cpp" INCLUDE_DIRS "."
    REQUIRES mounam_dsp esp_driver_i2s esp_driver_uart esp_driver_gpio esp_timer esp_psram)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Werror)
