-- Runs on the GL thread before game_start. Observe the official health-advice sprite.
local ok,visible=pcall(function()
    local update=rawget(_G,'FileUpdate_Instance')
    local node=update and update.flash_png
    if not node or not tolua or tolua.isnull(node) then return false end
    local scene=cc.Director:getInstance():getRunningScene()
    -- Detached, hidden, faded, or retained nodes from an old scene are not the splash.
    for _=1,32 do
        if not node or tolua.isnull(node) or not node:isVisible() or node:getOpacity()<=0 then return false end
        if node==scene then return true end
        node=node:getParent()
    end
    return false
end)
return ok and visible and 1 or 0
