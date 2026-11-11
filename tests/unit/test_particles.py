from src.visualization.particles import NeutronField


def test_neutron_field_syncs_and_updates_without_crash() -> None:
    field = NeutronField(max_particles=40)
    bounds = (10.0, 10.0, 200.0, 200.0)
    field.sync_population(25, bounds)
    assert len(field.particles) == 25

    field.update(
        dt=0.016,
        bounds=bounds,
        rod_rects=[(50.0, 50.0, 20.0, 40.0)],
        fuel_points=[(80.0, 80.0)],
        scram_active=False,
        keff=1.1,
    )
    assert len(field.particles) <= 40
