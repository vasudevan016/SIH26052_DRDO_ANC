CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Werror -pedantic
DSP = components/mounam_dsp
CPP = $(DSP)/mounam_dsp.cpp
HEADERS = $(wildcard $(DSP)/include/*.h)

.PHONY: all test sanitize benchmark clean
all: build/libmounam.so build/test_dsp

build:
	mkdir -p build

build/libmounam.so: $(CPP) host/c_api.cpp $(HEADERS) | build
	$(CXX) $(CXXFLAGS) -fPIC -shared -I$(DSP)/include $(CPP) host/c_api.cpp -o $@

build/test_dsp: $(CPP) tests/test_dsp.cpp $(HEADERS) | build
	$(CXX) $(CXXFLAGS) -I$(DSP)/include $(CPP) tests/test_dsp.cpp -o $@

test: all
	./build/test_dsp
	python3 -m unittest discover -s tests -p 'test_*.py' -v

sanitize: | build
	$(CXX) $(CXXFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer -I$(DSP)/include $(CPP) tests/test_dsp.cpp -o build/test_dsp_sanitize
	./build/test_dsp_sanitize

benchmark: | build
	$(CXX) $(CXXFLAGS) -I$(DSP)/include $(CPP) tests/benchmark_dsp.cpp -o build/benchmark_dsp
	./build/benchmark_dsp

clean:
	rm -rf build
