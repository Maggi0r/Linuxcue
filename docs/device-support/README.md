# Adding New Corsair Devices

linuxcue should feel like an end-user application, not like a developer tool. Unknown Corsair devices are therefore shown in the GUI, but writes stay disabled until the device is mapped safely.

## User Flow
1. Connect the Corsair/iCUE device.
2. Open linuxcue.
3. Select the unknown device card.
4. Click `Geraetebericht speichern`.
5. Choose a location where the JSON file is easy to find, for example `Downloads`.
6. Open a GitHub `Device support request` issue and attach the generated `linuxcue-device-report-*.json` file.

## Developer Flow
1. Put the JSON report somewhere local.
2. Run:

```bash
linuxcue prepare-device-support ~/linuxcue-device-report-unknown-1b1c-xxxx.json
```

3. Review the generated folder under `docs/device-support/<slug>/`.
4. Copy the generated `KnownDevice` snippet into `src/linuxcue/known_devices.py`.
5. Keep `support_level="detected"` until captures confirm real control packets.
6. Add backend and GUI support feature by feature.

## Support Levels
- `detected`: Device is visible, but linuxcue does not write to it.
- `scaffolding`: Profile/UI shape exists, but packets are not fully confirmed.
- `descriptor-mapped`: HID descriptors and feature reports are mapped.
- `live-write`: linuxcue can safely write confirmed commands.

## Safety Rule
Never send RGB, DPI, EQ, fan, macro, or memory commands to a new model just because another Corsair device uses a similar packet. Start read-only, capture before/after behavior, then enable writes one feature at a time.
