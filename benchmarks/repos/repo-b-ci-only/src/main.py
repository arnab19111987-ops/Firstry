"""CI project main module."""


def process_data(data: list[str]) -> list[str]:
    """Process a list of strings."""
    return [item.strip().upper() for item in data if item.strip()]


def validate_config(config: dict[str, str]) -> bool:
    """Validate configuration dictionary."""
    required_keys = {"name", "version", "author"}
    return all(key in config for key in required_keys)


class DataProcessor:
    """Process and validate data."""

    def __init__(self, config: dict[str, str]):
        if not validate_config(config):
            raise ValueError("Invalid configuration")
        self.config = config
        self.processed_count = 0

    def process(self, items: list[str]) -> list[str]:
        """Process items and track count."""
        result = process_data(items)
        self.processed_count += len(result)
        return result

    def get_stats(self) -> dict[str, int]:
        """Get processing statistics."""
        return {"processed_count": self.processed_count}


if __name__ == "__main__":
    config = {"name": "test", "version": "1.0", "author": "tester"}
    processor = DataProcessor(config)

    sample_data = ["  hello  ", "world", "", "python"]
    result = processor.process(sample_data)
    print(f"Processed: {result}")
    print(f"Stats: {processor.get_stats()}")
