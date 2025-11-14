-- Gas Purity Historical
from(bucket: "electrolyzer_data")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bga")
  |> filter(fn: (r) => r._field == "primary_pct")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ 
      r with 
      _field: if r.device == "bga1" then "BGA01" 
              else if r.device == "bga2" then "BGA02"
              else "Purity %"
  }))
  |> keep(columns: ["_time", "_value", "_field"])

-- Gas Pairs
from(bucket: "electrolyzer_data")
  |> range(start: -1m)
  |> filter(fn: (r) => r._measurement == "bga")
  |> filter(fn: (r) => r._field == "primary_gas" or r._field == "secondary_gas")
  |> last()
  |> group()
  |> pivot(rowKey:["device"], columnKey: ["_field"], valueColumn: "_value")
  |> reduce(
      fn: (r, accumulator) => ({
          "BGA01 PG": if r.device == "bga1" and exists r.primary_gas then r.primary_gas else accumulator["BGA01 PG"],
          "BGA01 SG": if r.device == "bga1" and exists r.secondary_gas then r.secondary_gas else accumulator["BGA01 SG"],
          "BGA02 PG": if r.device == "bga2" and exists r.primary_gas then r.primary_gas else accumulator["BGA02 PG"],
          "BGA02 SG": if r.device == "bga2" and exists r.secondary_gas then r.secondary_gas else accumulator["BGA02 SG"]
      }),
      identity: {"BGA01 PG": "NA", "BGA01 SG": "NA", "BGA02 PG": "NA", "BGA02 SG": "NA"}
  )
  |> keep(columns: ["BGA01 PG", "BGA01 SG", "BGA02 PG", "BGA02 SG"])

-- Temperature Historical
from(bucket: "electrolyzer_data")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => 
      (r._measurement == "modbus" and r.name == "temperature_controller") or 
      (r._measurement == "bga" and r._field == "temperature_c")
  )
  |> filter(fn: (r) => r._value < 1000)
  |> map(fn: (r) => ({ 
      r with 
      _field: if r._measurement == "bga" and r.device == "bga1" then "BGA01"
              else if r._measurement == "bga" and r.device == "bga2" then "BGA02"
              else r._field 
  }))
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> keep(columns: ["_time", "_value", "_field"])

  -- Analog Input Historical
  from(bucket: "electrolyzer_data")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "analog_inputs")
  |> filter(fn: (r) => r._field =~ /^AI0[1-8]$/)
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> keep(columns: ["_time", "_value", "_field"])

  -- Analog Input Gauges