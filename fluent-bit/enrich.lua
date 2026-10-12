function enrich(tag, ts, record)
  local s = tonumber(record["status"])
  if s ~= nil then
    record["status_class"] = tostring(math.floor(s / 100)) .. "xx"
    if record["request_time"] ~= nil and tonumber(record["request_time"]) > 1.0 then record["slow"] = true end
  end
  return 1, ts, record
end
