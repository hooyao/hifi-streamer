-- Experimental WirePlumber 0.4 diagnostic override; not installed by default.
-- Its effect on audio stability still requires measurement and listening tests.
table.insert(alsa_monitor.rules, {
  matches = {
    { { "node.name", "matches", "alsa_output.usb-*" } },
  },
  apply_properties = {
    ["api.alsa.period-size"] = 1024,
    ["api.alsa.headroom"] = 8192,
    ["session.suspend-timeout-seconds"] = 0,
  },
})
