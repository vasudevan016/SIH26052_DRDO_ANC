idf_component_register(SRCS "mounam_dsp.cpp" "neural.cpp" INCLUDE_DIRS "include")
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
target_compile_options(${COMPONENT_LIB} PRIVATE -O2 -Wall -Wextra)
