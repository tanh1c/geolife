# Data setup

This repository does **not** redistribute Microsoft GeoLife GPS Trajectories.

## Dataset

Use **GeoLife GPS Trajectories 1.3** from the official Microsoft Download Center.

Expected extracted layout:

```text
Geolife Trajectories 1.3/
└── Data/
    ├── 000/
    │   ├── Trajectory/
    │   │   └── *.plt
    │   └── labels.txt   # only for some users
    ├── 001/
    └── ...
```

Each PLT file has six header lines. Data rows contain latitude, longitude, an unused field, altitude in feet, a serial date, a date string, and a time string. The v1.3 guide documents timestamps as GMT/UTC and altitude `-777` as invalid.

## Licensing and privacy

The supplied Microsoft Research license is for non-commercial use and includes redistribution restrictions. Keep the raw dataset outside Git. Do not commit `.plt` files, extracted point tables, or user-level trajectory exports to this public repository.

Derived data and visualizations may also carry privacy/licensing implications. Keep generated EDA outputs local by default and review them before publishing.

## Local path

Set:

```bash
export GEOLIFE_DATA_ROOT="/path/to/Geolife Trajectories 1.3/Data"
```

On Windows PowerShell:

```powershell
$env:GEOLIFE_DATA_ROOT = "C:\path\to\Geolife Trajectories 1.3\Data"
```

For Modal, see `notebooks/README.md`.
