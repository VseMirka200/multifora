from dataclasses import dataclass, field


@dataclass(slots=True)
class OperationResult:
    new_files: list = field(default_factory=list)
    updated_files: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "new_files": self.new_files,
            "updated_files": self.updated_files,
            "errors": self.errors,
        }

    def get(self, key, default=None):
        return self.as_dict().get(key, default)

    def __getitem__(self, key):
        return self.as_dict()[key]

    def __contains__(self, key):
        return key in self.as_dict()
