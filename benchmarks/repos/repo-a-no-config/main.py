"""Small test package for benchmarking."""

def hello_world():
    """Basic hello world function."""
    return "Hello, World!"

def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

def fibonacci(n: int) -> int:
    """Calculate fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    """Simple calculator class."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a: float, b: float) -> float:
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
    
    def get_history(self) -> list:
        return self.history.copy()

if __name__ == "__main__":
    print(hello_world())
    print(f"2 + 3 = {add_numbers(2, 3)}")
    print(f"fibonacci(10) = {fibonacci(10)}")
    
    calc = Calculator()
    print(f"calc.add(5, 3) = {calc.add(5, 3)}")
    print(f"calc.multiply(4, 7) = {calc.multiply(4, 7)}")
    print(f"History: {calc.get_history()}")