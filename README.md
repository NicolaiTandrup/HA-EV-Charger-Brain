# EV Charger Brain

A native, local Home Assistant custom integration that associates vehicles with
physical chargers using explicit HA device/entity mappings. **Read-only / Log
only:** this version never calls a charging service, changes helpers or controls
hardware. It is a development first phase, not a production charger controller.

The original Node-RED flow remains unchanged under `node-red/`. See the
[architecture decision and complete audit](docs/adr-001-native-read-only.md) and
[versioned association contract](docs/association-contract-v1.md).

## Installation and configuration

Requires Home Assistant **2026.10.0+** (tested on 2026.10.2), using existing charger
and vehicle integrations. No Node-RED or extra integration runtime dependencies.
Python 3.14 is required for local development against the tested HA version.

For manual development installation, copy only `custom_components/ev_charger_brain`
to HA's `config/custom_components/ev_charger_brain`, restart HA, then open
**Settings → Devices & services → Add integration → EV Charger Brain**. Do this
on a test instance first. This task does not deploy to the owner's HA instance.

1. Add each vehicle with a stable ID, name, primary device, charge-cable binary
   sensor and device tracker. Optionally select a separate fallback device and
   its corresponding source entities (e.g. Tesla Custom primary and Fleet fallback).
2. Add each charger with a stable ID/name, physical device, exact status sensor,
   enabled switch, and exact tracker state for the site's zone. Multiple chargers
   can share a site; distinct sites use distinct tracker states. Any manufacturer
   providing the supported source semantics can be used.
3. Optionally select an input_boolean as a read-only manual-until-disconnect signal.
4. Select **Validate and save** and set the source freshness limit. Required
   entities must exist and source registry device ownership must match selection.
   Helpers do not require device ownership. Duplicate IDs/sources are rejected.

Options allow adding/removing mappings and changing freshness. To edit a mapping,
remove it and add it with the same stable ID before saving; existing entities retain
identity. Use a single integration entry for all sites. Options reload the engine,
so it reconstructs sessions conservatively; do not edit during a critical session.

Example UI mapping (illustrative, not YAML configuration):

| Field | Charger example | Vehicle example |
| --- | --- | --- |
| ID | station_1 | vehicle_a |
| Device | actual charger device | actual primary vehicle device |
| Status / cable | sensor.station_status | binary_sensor.vehicle_cable |
| Enabled / tracker | switch.station_enabled | device_tracker.vehicle_location |
| Exact tracker zone state | home | — |

For the owner's Garage, the reported entities are `sensor.garage_status` and
`switch.garage_charger_enabled`; verify both belong to the intended charger.
The export's `switch.garage_is_enabled` must not be copied. No IDs are derived.

The initial status vocabulary accepts charging, ready_to_charge, awaiting_start,
completed/complete, car_disconnected/disconnected (spaces and hyphens normalize).
Cable sources must use on/off. Zone states are exact, case-sensitive tracker
states, not zone entity IDs. Other charger protocols need an explicit adapter or
separately scoped configurable state vocabulary; unsupported values fail closed.

## Entities and use

The aggregate Sensor defaults to `sensor.ev_charger_assignments` and publishes
schema_version 1, evaluation time, valid assignments and all charger outcomes.
Each charger gets an **Association valid** Binary Sensor and a service device;
source devices are never reparented. IDs are stable per entry + charger ID.
Select the actual entity ID in dashboards/automations; HA may suffix or rename it.
No Honeycomb installation is needed. Honeycomb consumers must make this source
optional and implement freshness/validity checks from the contract.

No candidate is assigned if either side of the graph is ambiguous. Fresh cable on
and a matching site are required for a new association. Once established, physical
disconnect is authoritative: GPS unknown/not_home or cable off does not terminate
the session. Missing or stale cable/status suppress publication until recovery.
Manual override preserves an existing identity; it does not select a vehicle or
turn anything on. It latches until observed physical disconnect. An on helper at
disconnect must cycle off/on to rearm because Brain cannot reset helpers.

## Development and validation

```sh
uv venv --python 3.14 .venv
uv pip sync --python .venv/bin/python --require-hashes requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check custom_components tests
.venv/bin/ruff format --check custom_components tests
```

The hashed dependency file pins HA 2026.10.2 and its matching custom-integration
test harness. Tests exercise synthetic sources in real HA fixtures: config/options,
setup/unload, published entities, diagnostics, association transitions and no service
calls. No credentials or owner instance are required. GitHub Actions additionally
registers official hassfest and HACS validation; pending CI results are not a pass.

## HACS status

The repository contains the custom-component layout, versioned manifest, English
UI translations, README and hacs.json. No catalog submission or release is made.
Official hassfest passes locally; GitHub HACS validation must also pass on the PR
before calling this HACS validated.
Once the branch is available, HACS **Custom repositories → repository URL →
Integration**, download the development revision if offered, restart HA and add
the integration as above. If HACS only offers the unchanged default branch, use
manual installation until this code is merged or an approved prerelease exists.
Never install the default branch expecting native files before they are present.

## Limitations and differences from Node-RED

* No Production or Disabled selector, charging commands, notifications or CSV
  writer; HA entity history can record observable outcomes.
* No historical replug shortcut, default-car tiebreaker, recent cable-on grace or
  pending timeout. Fresh evidence replaces guesses, and ambiguous stays ambiguous.
* Primary on/off or zone state wins; fallback is used only when primary is unusable.
  This differs from the reference's effective OR across providers.
* Restart/options reload reconstructs only from fresh state. Unknown GPS may leave
  an active charger unassigned; manual latch history is not durable if its helper
  is off. Last identity never becomes current confirmation after restart/replug.
* Source freshness is only as reliable as the provider's reports. No HA connection
  outside the process exists; HA shutdown stops evaluation. Consumers must expire
  cached results. No real hardware or household mapping has been tested here.
* English translation is provided; additional locales and UI illustrations remain.
* Honeycomb NG issue #126 coordination is pending; v1 is a documented proposal.

## Troubleshooting, migration and rollback

A rejected mapping usually means wrong device, missing entity, wrong domain or
reused ID/source. Check each entity's device in HA, including Fleet's separate
device. Missing sources at startup retry; invalid device ownership requires options
repair. Unknown status stays unavailable; review your charger's actual vocabulary.
For pending/ambiguous/stale results, inspect source age, on/off values, exact zone
state, and competing chargers/vehicles. GPS is needed for new matches, not to keep
an existing session. Anonymous diagnostics include counts/modes only, without
names, source IDs, locations or raw config/state.

Back up HA and the existing Node-RED flow. Leave existing charging automation
unchanged; observe native results alongside it in a test instance, then a separately
approved household trial. Verify every mapping, ambiguous/replug/disconnect/restart
case and provider report cadence. Do not enable production controls (none exist).
Rollback: remove/disable this integration, restart if removing its directory, and
continue using the untouched Node-RED baseline. There are no physical or helper
changes to reverse. Owners must approve a separate production-control phase.

The new native implementation, documentation and brand artwork are MIT licensed.
The imported Node-RED reference is retained as received; this change does not
alter or assert a new license for that baseline.
