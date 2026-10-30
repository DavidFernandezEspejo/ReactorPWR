from pydantic import BaseModel, ConfigDict, Field, model_validator


class CoreState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    sim_time: float = Field(default=0.0, ge=0.0)
    active_neutrons: int = Field(default=1000, ge=0)
    control_rods_pct: float = Field(default=50.0, ge=0.0, le=100.0)
    coolant_flow: float = Field(default=18000.0, gt=0.0)
    coolant_temp_celsius: float = Field(default=290.0, ge=0.0)
    keff: float = Field(default=1.0, ge=0.0)
    electric_power_mwe: float = Field(default=0.0, ge=0.0)
    scram_active: bool = False

    @model_validator(mode="after")
    def check_scram_condition(self) -> "CoreState":
        # Umbral de seguridad para el Suceso de Parada de Emergencia
        if self.coolant_temp_celsius > 350.0:
            object.__setattr__(self, "control_rods_pct", 100.0)
            object.__setattr__(self, "scram_active", True)
        elif self.control_rods_pct < 100.0:
            object.__setattr__(self, "scram_active", False)
        return self
