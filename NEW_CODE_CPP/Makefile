CXX = g++
CXXFLAGS = -O3 -std=c++17 -Wall -Wextra -pthread

TARGET = solver
SRCS = solver.cpp
OBJS = $(SRCS:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(TARGET) $(OBJS)

test: $(TARGET)
	./$(TARGET) ../datasets/satlib_uf50/uf50-01.cnf
