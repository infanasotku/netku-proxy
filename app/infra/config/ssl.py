from pydantic import BaseModel, computed_field, Field


class SSLSettings(BaseModel):
    root_certificates_strings: str | None = Field(default=None)

    @computed_field
    @property
    def root_certificates(self) -> list[str] | None:
        if self.root_certificates_strings is None:
            return None
        return self.root_certificates_strings.split()
