-- Staging-only probe. Appending this to the recovered game_start is not deployment.
-- Emits a local marker only; does not query models, send packets, or install hooks.
do
    local ok, err = pcall(function()
        local fu = cc.FileUtils:getInstance()
        local path = fu:getWritablePath() .. "dldl_loader_probe.txt"
        local output = assert(io.open(path, "w"))
        output:write("probe=dldl_loader_v1\n")
        output:write("loaded_at=", tostring(os.time()), "\n")
        output:write("game_start=", tostring(fu:fullPathForFilename("game_start.luac")), "\n")
        output:close()
    end)
    if not ok then print("[dldl_loader_probe] " .. tostring(err)) end
end
