# Experimental sensor integration

No physical sensor is connected or calibrated by this repository. The cloud handler
accepts telemetry only through the optional AWS IoT rule; no public sensor HTTP route exists.

1. Enable `EnableSensors=true` in the stack.
2. In the cloud administrator workspace, register a device with a gate/room assignment.
3. Run `python scripts/provision_sensor.py --device school-gate-1 --table YOUR_APP_TABLE`.
4. Copy the generated certificate/private key to the device through a secure local process.
   Use the official Amazon Root CA for TLS validation; never disable server certificate checks.
5. Configure the device MQTT client ID to exactly its registered device ID. Its policy
   permits only its own telemetry topic, not other schools/devices or subscriptions.
6. Synchronize time with NTP. Sample the PM module according to its documented warm-up,
   checksum and maintenance requirements. Publish five-minute summaries, not random values.
7. Validate placement and perform a collocation study before relying on measurements.

Example **schema only**, not a real observation:

```json
{
  "observedAt": "2026-10-10T03:00:00+00:00",
  "pm25": 42.1,
  "humidity": 56.0,
  "sampleCount": 60,
  "sequence": 123
}
```

Publish over MQTT/TLS on port 8883 to `airguardian/DEVICE_ID/telemetry`.
`deviceId` is injected from the authenticated topic; a submitted `school` field is ignored.
The handler maps the device to the school registered by its administrator.

Buffer at most one day on a device, preserving observation times and sequence numbers.
Replayed old samples do not overwrite the latest sensor state. A reboot can reset
sequence numbers because deduplication includes the observation timestamp as well.

The health view flags stale data, inadequate sample counts, high humidity, abrupt
changes and prolonged identical readings. These heuristics do not establish accuracy.
Sensor measurements remain separate from the school-area planning feed until field
calibration and school approval justify changing that policy.

Hardware firmware is device-specific and is not supplied as a pretend universal driver.
Use the module vendor's supported library for the purchased sensor and verify checksums,
power behavior, enclosure ventilation, and safe outdoor installation.

To retire a device, set its registry `active` to false and deactivate its AWS IoT
certificate. Registry deactivation alone does not stop it consuming IoT messaging quota.
