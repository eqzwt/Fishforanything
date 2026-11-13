-- Fish For Anything UI - "Midnight Tackle" style.
-- Deep charcoal panels with thin neon outlines, bold-italic headings, dark tiles that glow with their
-- rarity colour from the bottom, outlined tab pills, and smooth fade/scale transitions. Every menu is built
-- from the same handful of helpers below, so the whole game shares one look.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local StarterGui = game:GetService("StarterGui")
local GuiService = game:GetService("GuiService")
local Config = require(ReplicatedStorage.Shared.Config)
local FishModels = require(ReplicatedStorage.Shared.FishModels)

local UI = {}
local player = Players.LocalPlayer
local rgb = Color3.fromRGB
local fmt = Config.FormatMoney
local WHITE = rgb(255, 255, 255)

------------------------------------------------------------------ design tokens (one palette everywhere)
local C = {
	-- surfaces
	Panel = rgb(16, 18, 27), Panel2 = rgb(23, 26, 38), Panel3 = rgb(33, 37, 54), Well = rgb(10, 11, 17),
	Edge = rgb(58, 63, 88), EdgeHi = rgb(96, 104, 140), Ink = rgb(6, 7, 12),
	-- text
	Text = WHITE, Sub = rgb(162, 170, 198), Cream = rgb(255, 238, 196),
	-- neon accents
	Accent = rgb(112, 214, 255), Gold = rgb(255, 212, 110), Green = rgb(132, 236, 150), Orange = rgb(255, 166, 84),
	Purple = rgb(204, 128, 255), Pink = rgb(255, 128, 204), Red = rgb(255, 92, 92), Off = rgb(92, 98, 124),
}
UI.Colors = C
local HEAD = Font.new("rbxasset://fonts/families/SourceSansPro.json", Enum.FontWeight.Bold, Enum.FontStyle.Italic)
local BODY = Font.new("rbxasset://fonts/families/SourceSansPro.json", Enum.FontWeight.SemiBold)
local RADIUS = 5 -- nearly square corners, like the reference
local GRAIN = "rbxassetid://119952696876196" -- soft tileable grunge so big surfaces aren't flat
local function grain(parent, alpha, z)
	local g = Instance.new("ImageLabel")
	g.Name = "Grain"
	g.BackgroundTransparency = 1
	g.Image = GRAIN
	g.ImageTransparency = 1 - (alpha or 0.1)
	g.ScaleType = Enum.ScaleType.Tile
	g.TileSize = UDim2.fromOffset(256, 256)
	g.Size = UDim2.fromScale(1, 1)
	g.ZIndex = z or parent.ZIndex
	g.Parent = parent
	return g
end

-- item art: a muted, themed picture that sits behind the item's name (rods, bait, chum)
local ICONS = {
	Rod_Bamboo = 116916018365987, Rod_Driftwood = 82295268065727, Rod_Fiberglass = 77534130351497, Rod_Carbon = 74685754008434,
	Rod_CoralReef = 87841585280443, Rod_DeepSea = 102518439085150, Rod_Golden = 79803407093077, Rod_Stormcaller = 124448512161261,
	Rod_Abyssal = 132058795566384, Rod_Celestial = 137507296757786, Rod_Leviathan = 107850461499207,
	Bait_Worm = 70801404314113, Bait_Minnow = 79198491834122, Bait_Shrimp = 108862341364053, Bait_GlowWorm = 135954374241892,
	Bait_Lucky = 100751089030534, Bait_Golden = 94483244195280,
	Chum_Basic = 103907302874223, Chum_Premium = 99046417406091, Chum_Lucky = 101635185413295,
}
UI.Icons = ICONS

UI.Data = nil
local handlers
local gui, root, scaleObj
local refs = {}
local panels = {}
local openPanel

------------------------------------------------------------------ helpers
local function make(class, props, parent)
	local o = Instance.new(class)
	for k, v in props do o[k] = v end
	if parent then o.Parent = parent end
	return o
end
local function round(o, r) return make("UICorner", { CornerRadius = UDim.new(0, r or RADIUS) }, o) end
local function stroke(o, c, t, tr)
	local s = o:FindFirstChildOfClass("UIStroke")
	if not s then s = make("UIStroke", { ApplyStrokeMode = Enum.ApplyStrokeMode.Border, LineJoinMode = Enum.LineJoinMode.Round }, o) end
	s.Color = c or C.Edge
	s.Thickness = t or 1.5
	s.Transparency = tr or 0
	return s
end
local function pad(o, p) return make("UIPadding", { PaddingLeft = UDim.new(0, p), PaddingRight = UDim.new(0, p), PaddingTop = UDim.new(0, p), PaddingBottom = UDim.new(0, p) }, o) end
local function tween(o, t, props, style, dir)
	local tw = TweenService:Create(o, TweenInfo.new(t, style or Enum.EasingStyle.Quint, dir or Enum.EasingDirection.Out), props)
	tw:Play()
	return tw
end
local function text(parent, props)
	local t = make("TextLabel", { BackgroundTransparency = 1, FontFace = BODY, TextColor3 = C.Text, TextSize = 15, TextXAlignment = Enum.TextXAlignment.Left, Text = "",
		TextStrokeColor3 = C.Ink, TextStrokeTransparency = 0.75 }, parent)
	for k, v in props do t[k] = v end
	return t
end
-- bold italic heading text
local function title(parent, props)
	local t = text(parent, props)
	t.FontFace = HEAD
	if props.TextStrokeTransparency == nil then t.TextStrokeTransparency = 0.55 end
	return t
end
-- a dark surface (optionally with a subtle top-lit shade)
local function frame(parent, props, r, flat)
	local f = make("Frame", { BackgroundColor3 = C.Panel2, BorderSizePixel = 0 }, parent)
	for k, v in props do f[k] = v end
	round(f, r or RADIUS)
	if not flat then
		make("UIGradient", { Name = "Shade", Rotation = 90, Color = ColorSequence.new(WHITE, rgb(200, 202, 214)) }, f)
	end
	return f
end
-- a soft glow of `color` rising from the bottom of a surface
local function tint(parent, color, strength, z)
	local t = make("Frame", { Name = "Tint", BackgroundColor3 = color, BorderSizePixel = 0, AnchorPoint = Vector2.new(0, 1), Position = UDim2.fromScale(0, 1),
		Size = UDim2.fromScale(1, 0.6), ZIndex = z or parent.ZIndex }, parent)
	round(t, RADIUS)
	make("UIGradient", { Rotation = 90, Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, 1 - (strength or 0.45)) }) }, t)
	return t
end
-- dark tile with a thin outline; `accent` tints the outline and the bottom glow
local function tile(parent, props, accent, z)
	local f = frame(parent, props, RADIUS, true)
	f.BackgroundColor3 = props.BackgroundColor3 or C.Panel2
	stroke(f, accent and accent:Lerp(C.Edge, 0.35) or C.Edge, 1.5, 0)
	if accent then tint(f, accent, 0.42, z or f.ZIndex) end
	return f
end
-- hover / press feel shared by every button: gentle scale, brighter outline, faint fill
local function interact(b, st, accent, sc)
	local hover, down = false, false
	local base = b.BackgroundColor3
	local function upd()
		tween(sc, 0.16, { Scale = down and 0.96 or (hover and 1.03 or 1) }, Enum.EasingStyle.Quad)
		tween(st, 0.16, { Color = hover and accent:Lerp(WHITE, 0.35) or accent, Thickness = hover and 2 or 1.5 }, Enum.EasingStyle.Quad)
		tween(b, 0.16, { BackgroundColor3 = hover and base:Lerp(accent, 0.12) or base }, Enum.EasingStyle.Quad)
	end
	b.MouseEnter:Connect(function() hover = true upd() end)
	b.MouseLeave:Connect(function() hover = false down = false upd() end)
	b.MouseButton1Down:Connect(function() down = true upd() end)
	b.MouseButton1Up:Connect(function() down = false upd() end)
	b.SelectionGained:Connect(function() hover = true upd() end)
	b.SelectionLost:Connect(function() hover = false upd() end)
end
-- outlined button: dark fill, neon outline + text in its accent colour.
-- (BackgroundColor3 passed in is treated as the button's accent colour)
local function button(parent, props, onClick)
	local accent = props.BackgroundColor3 or C.Accent
	local b = make("TextButton", { AutoButtonColor = false, BackgroundColor3 = C.Panel2, BorderSizePixel = 0, FontFace = HEAD, TextSize = 16, Text = "",
		TextStrokeColor3 = C.Ink, TextStrokeTransparency = 0.6, SelectionImageObject = nil }, parent)
	for k, v in props do if k ~= "Corner" and k ~= "BackgroundColor3" and k ~= "TextColor3" then b[k] = v end end
	b.TextColor3 = props.TextColor3 or accent:Lerp(WHITE, 0.2)
	round(b, props.Corner and math.min(props.Corner, RADIUS) or RADIUS)
	local st = stroke(b, accent, 1.5, 0)
	tint(b, accent, 0.18, b.ZIndex)
	b:SetAttribute("Accent", accent)
	interact(b, st, accent, make("UIScale", {}, b))
	if onClick then
		b.Activated:Connect(function()
			handlers.Click()
			onClick()
		end)
	end
	return b
end
-- recolour an existing outlined button (selection states)
local function setAccent(b, accent, filled)
	local st = b:FindFirstChildOfClass("UIStroke")
	if st then st.Color = accent end
	b.TextColor3 = accent:Lerp(WHITE, 0.2)
	local t = b:FindFirstChild("Tint")
	if t then
		t.BackgroundColor3 = accent
		t.UIGradient.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, filled and 0.45 or 0.82) })
	end
end
-- muted item picture filling its tile (text goes on top)
local function art(parent, key, tint, z, alpha, scale)
	local id = ICONS[key]
	if not id then return nil end
	return make("ImageLabel", { Name = "Art", BackgroundTransparency = 1, AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.fromScale(scale or 0.94, scale or 0.94), Image = "rbxassetid://" .. id, ImageColor3 = (tint or WHITE):Lerp(WHITE, 0.5),
		ImageTransparency = alpha or 0.6, ScaleType = Enum.ScaleType.Fit, ZIndex = z or parent.ZIndex }, parent)
end
-- tile label: "Bamboo Rod" -> "Bamboo"
local function shortName(name) return (name:gsub(" Rod$", "")) end

local function act(name, a, b)
	local res = handlers.Action(name, a, b)
	if type(res) == "table" and res.msg then UI.Notify(res.msg, res.ok and C.Green or C.Red) end
	return res
end
local function rarityColor(r) return Config.RarityByName[r].Color end

-- 3D fish inside a ViewportFrame (side view)
local function fishViewport(parent, speciesId, props, silhouette)
	local vp = make("ViewportFrame", { BackgroundTransparency = 1, Ambient = rgb(175, 180, 190), LightColor = rgb(255, 250, 240), LightDirection = Vector3.new(-0.3, -1, -0.4) }, parent)
	for k, v in props do vp[k] = v end
	local model = FishModels.Build(speciesId, 4)
	if silhouette then
		for _, d in model:GetDescendants() do
			if d:IsA("MeshPart") then d.TextureID = "" d.Color = rgb(30, 34, 50) d.Material = Enum.Material.SmoothPlastic
			elseif d:IsA("BasePart") then d.Color = rgb(30, 34, 50) d.Material = Enum.Material.SmoothPlastic
			elseif d:IsA("Decal") or d:IsA("SurfaceAppearance") then d:Destroy() end
		end
	end
	model:PivotTo(CFrame.new())
	model.Parent = vp
	local cam = make("Camera", { FieldOfView = 30 }, vp)
	local _, size = model:GetBoundingBox()
	local dist = math.max(size.Z, size.Y * 1.6) * 2.05
	cam.CFrame = CFrame.lookAt(Vector3.new(dist, dist * 0.12, 0), Vector3.zero)
	vp.CurrentCamera = cam
	return vp, model, cam
end

------------------------------------------------------------------ toasts
local toastHolder
function UI.Notify(msg, color, big)
	if not toastHolder then return end
	color = color or C.Accent
	local t = make("CanvasGroup", { Size = UDim2.fromOffset(0, big and 36 or 30), AutomaticSize = Enum.AutomaticSize.X, BackgroundColor3 = C.Panel, BorderSizePixel = 0,
		GroupTransparency = 1 }, toastHolder)
	round(t, RADIUS)
	stroke(t, color:Lerp(C.Edge, 0.3), 1.5, 0)
	tint(t, color, 0.25)
	make("UIPadding", { PaddingLeft = UDim.new(0, 16), PaddingRight = UDim.new(0, 16) }, t)
	text(t, { Size = UDim2.new(0, 0, 1, 0), AutomaticSize = Enum.AutomaticSize.X, Text = msg, TextColor3 = color:Lerp(WHITE, 0.5), FontFace = HEAD, TextSize = big and 18 or 15,
		TextXAlignment = Enum.TextXAlignment.Center })
	local sc = make("UIScale", { Scale = 0.92 }, t)
	tween(sc, 0.25, { Scale = 1 })
	tween(t, 0.2, { GroupTransparency = 0 })
	task.delay(big and 5 or 3, function()
		tween(t, 0.35, { GroupTransparency = 1 })
		task.wait(0.4)
		t:Destroy()
	end)
	local n = 0
	for _, c in toastHolder:GetChildren() do if c:IsA("CanvasGroup") then n += 1 end end
	if n > 4 then
		for _, c in toastHolder:GetChildren() do if c:IsA("CanvasGroup") then c:Destroy() break end end
	end
end

------------------------------------------------------------------ panels (one shared frame for every menu)
local PANEL_W, PANEL_H = 760, 470 -- every big menu uses the same size
local dim
local closingToken = 0
local function closePanels(instant)
	closingToken += 1
	local tk = closingToken
	for _, p in panels do
		if p.Visible then
			if instant then
				p.Visible = false
			else
				local sc = p:FindFirstChild("Pop")
				tween(sc, 0.14, { Scale = 0.96 }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
				tween(p, 0.14, { GroupTransparency = 1 }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
				task.delay(0.15, function() if tk == closingToken then p.Visible = false end end)
			end
		end
	end
	if dim then tween(dim, 0.2, { BackgroundTransparency = 1 }) end
	openPanel = nil
	if refs.Picker then refs.Picker.Visible = false end
	-- bring Old Gill's tutorial back if a menu had pushed it aside
	if refs.Tutorial and refs.TutHidden then refs.TutHidden = false refs.Tutorial.Visible = true end
end
UI.ClosePanels = function() closePanels() end

local function showPanel(name)
	closePanels(true)
	closingToken += 1
	local p = panels[name]
	p.Visible = true
	openPanel = name
	if refs.Tutorial and refs.Tutorial.Visible then refs.Tutorial.Visible = false refs.TutHidden = true end
	p.GroupTransparency = 1
	local sc = p:FindFirstChild("Pop")
	sc.Scale = 0.95
	tween(sc, 0.28, { Scale = 1 })
	tween(p, 0.22, { GroupTransparency = 0 })
	if dim then tween(dim, 0.25, { BackgroundTransparency = 0.55 }) end
	if UI.Data then UI.Update(UI.Data) end
end
local function togglePanel(name)
	if openPanel == name then closePanels() else showPanel(name) end
end
UI.TogglePanel = togglePanel
function UI.IsPanelOpen() return openPanel ~= nil end
function UI.OpenPanel() return openPanel end

-- big italic title, outlined close button; body below
local function makePanel(name, titleText, accent)
	accent = accent or C.Accent
	local p = make("CanvasGroup", { Name = name, AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.52), Size = UDim2.fromOffset(PANEL_W, PANEL_H),
		BackgroundColor3 = C.Panel, BorderSizePixel = 0, Visible = false, ZIndex = 10, GroupTransparency = 1 }, root)
	round(p, 8)
	stroke(p, C.Edge, 1.5, 0)
	make("UIScale", { Name = "Pop" }, p)
	grain(p, 0.14, 10)
	-- thin accent line along the very top
	local line = make("Frame", { Size = UDim2.new(1, 0, 0, 2), BackgroundColor3 = accent, BorderSizePixel = 0, ZIndex = 11 }, p)
	make("UIGradient", { Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.1), NumberSequenceKeypoint.new(0.6, 0.6), NumberSequenceKeypoint.new(1, 1) }) }, line)
	title(p, { Position = UDim2.fromOffset(22, 12), Size = UDim2.new(0, 360, 0, 40), Text = titleText, TextSize = 32, ZIndex = 12, TextStrokeTransparency = 0.3 })
	local close = button(p, { Text = "X", Size = UDim2.fromOffset(34, 34), AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -14, 0, 14), BackgroundColor3 = C.Red, TextSize = 20, ZIndex = 14 },
		function() closePanels() end)
	close.Name = "Close"
	local body = make("Frame", { Name = "Body", BackgroundTransparency = 1, Position = UDim2.fromOffset(18, 62), Size = UDim2.new(1, -36, 1, -78), ZIndex = 11 }, p)
	panels[name] = p
	return p, body
end

-- a recessed well that scrolling content sits in
local function well(parent, props)
	local w = frame(parent, props, RADIUS, true)
	w.BackgroundColor3 = C.Well
	w.BackgroundTransparency = 0.15
	stroke(w, C.Edge, 1, 0.4)
	grain(w, 0.06, w.ZIndex)
	return w
end
local function scroller(parent, props)
	local s = make("ScrollingFrame", { BackgroundTransparency = 1, BorderSizePixel = 0, ScrollBarThickness = 4, ScrollBarImageColor3 = C.EdgeHi, CanvasSize = UDim2.new(),
		AutomaticCanvasSize = Enum.AutomaticSize.Y, ZIndex = 11 }, parent)
	for k, v in props do s[k] = v end
	return s
end
-- outlined tab pill row; returns { [name] = button }
local function tabRow(parent, list, onPick, x, y)
	local row = make("Frame", { Position = UDim2.fromOffset(x or 0, y or 0), Size = UDim2.new(1, -(x or 0), 0, 34), BackgroundTransparency = 1, ZIndex = 12 }, parent)
	make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 8), VerticalAlignment = Enum.VerticalAlignment.Center, SortOrder = Enum.SortOrder.LayoutOrder }, row)
	local out = {}
	for i, t in list do
		out[t[1]] = button(row, { Size = UDim2.fromOffset(t[3] or 94, 32), Text = t[1], TextSize = 17, ZIndex = 13, BackgroundColor3 = t[2], LayoutOrder = i }, function() onPick(t[1]) end)
	end
	return out, row
end
local function setTabs(tabs, active)
	for name, b in tabs do
		local acc = b:GetAttribute("Accent")
		setAccent(b, active == name and acc or acc:Lerp(C.Off, 0.55), active == name)
	end
end

------------------------------------------------------------------ custom hotbar
local hot = { slots = {}, items = {}, sig = nil }
local function getHum()
	local c = player.Character
	return c and c:FindFirstChildOfClass("Humanoid")
end
local function heldRodId()
	local c = player.Character
	local t = c and c:FindFirstChildOfClass("Tool")
	return t and t:GetAttribute("RodId")
end
local function findRodTool(id)
	for _, cont in { player.Character, player:FindFirstChildOfClass("Backpack") } do
		if cont then
			for _, t in cont:GetChildren() do
				if t:IsA("Tool") and t:GetAttribute("RodId") and (id == nil or t:GetAttribute("RodId") == id) then return t end
			end
		end
	end
end

-- small rod glyph in the rod's own colours (blank, grip, reel, line + bobber)
local function rodIcon(parent, r, z)
	local f = make("Frame", { BackgroundTransparency = 1, AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), Size = UDim2.fromOffset(40, 40), ZIndex = z }, parent)
	local blank = make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.56, 0.44), Size = UDim2.fromOffset(3, 42), Rotation = 45, BackgroundColor3 = r.Blank, BorderSizePixel = 0, ZIndex = z }, f)
	round(blank, 2)
	local grip = make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.25, 0.75), Size = UDim2.fromOffset(6, 14), Rotation = 45, BackgroundColor3 = r.Grip, BorderSizePixel = 0, ZIndex = z + 1 }, f)
	round(grip, 2)
	local reel = make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.42, 0.66), Size = UDim2.fromOffset(11, 11), BackgroundColor3 = r.Reel, BorderSizePixel = 0, ZIndex = z + 2 }, f)
	round(reel, 99) make("UIStroke", { Color = r.Accent, Thickness = 1.5 }, reel)
	make("Frame", { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.fromScale(0.93, 0.07), Size = UDim2.fromOffset(1, 17), BackgroundColor3 = rgb(220, 224, 235), BorderSizePixel = 0, ZIndex = z }, f)
	local bob = make("Frame", { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.93, 0, 0.07, 19), Size = UDim2.fromOffset(6, 6), BackgroundColor3 = rgb(235, 60, 60), BorderSizePixel = 0, ZIndex = z + 1 }, f)
	round(bob, 99)
	return f
end

local function showItemName(textStr, color)
	local l = refs.ItemName
	if not l then return end
	l.Text = textStr
	l.TextColor3 = color or C.Text
	l.TextTransparency = 0 l.TextStrokeTransparency = 0.4
	refs.ItemNameToken = (refs.ItemNameToken or 0) + 1
	local tk = refs.ItemNameToken
	task.delay(2.2, function()
		if tk ~= refs.ItemNameToken then return end
		tween(l, 0.5, { TextTransparency = 1, TextStrokeTransparency = 1 })
	end)
end

function UI.RefreshHotbar()
	local held = heldRodId()
	local aiming = UI.GetChumAim and UI.GetChumAim()
	for i, s in hot.slots do
		local it = hot.items[i]
		local sel = (it.Kind == "Rod" and held == it.Id) or (it.Kind == "Chum" and aiming == it.Id)
		if s.Sel ~= sel then
			s.Sel = sel
			tween(s.Stroke, 0.18, { Color = sel and WHITE or it.Edge, Thickness = sel and 2 or 1.5 })
			tween(s.Button, 0.18, { BackgroundColor3 = sel and C.Panel3 or C.Panel2 })
			s.Tint.UIGradient.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, sel and 0.3 or 0.6) })
			tween(s.Lift, 0.2, { Scale = sel and 1.06 or 1 })
		end
	end
end

local busy = false
local function selectSlot(i)
	local it = hot.items[i]
	if not it or busy then return end
	handlers.Click()
	local s = hot.slots[i]
	if s then
		s.Lift.Scale = 0.94
		tween(s.Lift, 0.25, { Scale = s.Sel and 1 or 1.06 })
	end
	if it.Kind == "Rod" then
		local hum = getHum()
		if not hum then return end
		local d = UI.Data
		if heldRodId() == it.Id then
			hum:UnequipTools()
			showItemName("Put away " .. it.Name, C.Sub)
		elseif d and d.EquippedRod == it.Id then
			local t = findRodTool(it.Id)
			if t then hum:EquipTool(t) end
			showItemName(it.Name .. "   " .. it.Stats, C.Gold)
		else
			busy = true
			task.spawn(function()
				local res = act("EquipRod", it.Id)
				if type(res) == "table" and res.ok then
					local t0 = os.clock()
					local t = findRodTool(it.Id)
					while not t and os.clock() - t0 < 2 do task.wait() t = findRodTool(it.Id) end
					local h = getHum()
					if t and h and t.Parent ~= player.Character then h:EquipTool(t) end
					showItemName(it.Name .. "   " .. it.Stats, C.Gold)
				end
				busy = false
				UI.RefreshHotbar()
			end)
		end
	elseif it.Kind == "Chum" then
		if UI.GetChumAim and UI.GetChumAim() == it.Id then
			if UI.CancelChumAim then UI.CancelChumAim() end
		else
			if UI.CancelChumAim then UI.CancelChumAim() end
			handlers.StartChumAim(it.Id)
			showItemName(it.Name .. "  •  click the water to throw", it.Color:Lerp(WHITE, 0.3))
		end
	end
	task.defer(UI.RefreshHotbar)
end
UI.SelectSlot = selectSlot

local SLOT = 72 -- hotbar tile size
-- tier colour for a rod: cheap rods cool, top rods hot
local function rodTier(r)
	local n = #Config.Rods
	local k = (r.Order - 1) / math.max(1, n - 1)
	if k < 0.2 then return C.Accent elseif k < 0.45 then return C.Green elseif k < 0.65 then return C.Gold elseif k < 0.85 then return C.Orange end
	return C.Purple
end

-- fit the hotbar to the screen (shrinks evenly when you own lots of gear), then keep the money
-- readout clear of it: lift it above the bar when they'd touch
local function fitWallet()
	local bar, money, wallet, hs = refs.Bar, refs.Money, refs.Wallet, refs.BarScale
	if not (bar and money and wallet and hs and root) then return end
	local s = scaleObj and scaleObj.Scale or 1
	local natural = bar.AbsoluteSize.X / math.max(hs.Scale, 0.01)
	local avail = root.AbsoluteSize.X - 28 * s
	hs.Scale = math.clamp(avail / math.max(natural, 1), 0.55, 1)
	local barRight = root.AbsolutePosition.X + root.AbsoluteSize.X / 2 + natural * hs.Scale / 2
	local textLeft = wallet.AbsolutePosition.X + wallet.AbsoluteSize.X - math.max(money.TextBounds.X, refs.BagText.TextBounds.X)
	local lifted = wallet:GetAttribute("Lifted") == true
	local clash = barRight > textLeft - 12 * s
	if clash ~= lifted then
		wallet:SetAttribute("Lifted", clash)
	end
	wallet.Position = UDim2.new(1, -18, 1, clash and -math.floor(SLOT * hs.Scale + 20) or -14)
end

local function rebuildHotbar(d)
	local items = {}
	for _, r in Config.Rods do
		if d.Rods[r.Id] then
			table.insert(items, { Kind = "Rod", Id = r.Id, Name = r.Name, Cfg = r, Color = rodTier(r),
				Stats = string.format("🍀x%.1f  💪x%.1f  🌊%s", r.Luck, r.Strength, Config.Zones[Config.RodZone(r)].Name) })
		end
	end
	for _, c in Config.Chum do
		local n = d.Chum[c.Id] or 0
		if n > 0 then table.insert(items, { Kind = "Chum", Id = c.Id, Name = c.Name, Cfg = c, Count = n, Color = c.Color }) end
	end
	local sig = {}
	for _, it in items do table.insert(sig, it.Id .. (it.Count or "")) end
	sig = table.concat(sig, ",")
	if sig == hot.sig then return end
	hot.sig = sig
	for _, s in hot.slots do s.Button:Destroy() end
	hot.slots = {}
	hot.items = items
	local bar = refs.HotSlots
	for i, it in items do
		it.Edge = it.Color:Lerp(C.Edge, 0.55)
		local b = make("TextButton", { AutoButtonColor = false, Text = "", BackgroundColor3 = C.Panel2, BorderSizePixel = 0, Size = UDim2.fromOffset(SLOT, SLOT), LayoutOrder = i, ZIndex = 3 }, bar)
		round(b, RADIUS)
		local st = stroke(b, it.Edge, 1.5, 0)
		local tn = tint(b, it.Color, 0.4, 3)
		local lift = make("UIScale", {}, b)
		local inner = make("Frame", { BackgroundTransparency = 1, Size = UDim2.fromScale(1, 1), ZIndex = 4 }, b)
		-- themed picture behind the item's name (like a trading-card tile)
		art(inner, (it.Kind == "Rod" and "Rod_" or "Chum_") .. it.Id, it.Color, 4, 0.58)
		title(inner, { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.new(0.5, 0, 0.5, 4), Size = UDim2.new(1, -6, 1, -16), Text = shortName(it.Name), TextSize = 15,
			TextWrapped = true, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 7, TextStrokeTransparency = 0.15 })
		if it.Kind == "Chum" then
			title(inner, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -4, 0, 2), Size = UDim2.fromOffset(40, 16), Text = "x" .. it.Count, TextSize = 14, TextXAlignment = Enum.TextXAlignment.Right, ZIndex = 7 })
		end
		local key = UserInputService.GamepadEnabled and not UserInputService.KeyboardEnabled and "" or tostring(i)
		title(inner, { Position = UDim2.fromOffset(5, 1), Size = UDim2.fromOffset(16, 16), Text = key, TextSize = 14, TextColor3 = C.Sub, ZIndex = 7 })
		local hover = make("UIScale", {}, inner)
		b.MouseEnter:Connect(function() tween(hover, 0.15, { Scale = 1.06 }) tween(st, 0.15, { Thickness = 2 }) showItemName(it.Name .. (it.Stats and ("   " .. it.Stats) or ("  x" .. (it.Count or 0))), C.Text) end)
		b.MouseLeave:Connect(function() tween(hover, 0.15, { Scale = 1 }) tween(st, 0.15, { Thickness = (hot.slots[i] and hot.slots[i].Sel) and 2 or 1.5 }) end)
		b.MouseButton1Down:Connect(function() tween(hover, 0.07, { Scale = 0.92 }, Enum.EasingStyle.Quad) end)
		b.MouseButton1Up:Connect(function() tween(hover, 0.18, { Scale = 1.06 }) end)
		b.Activated:Connect(function() selectSlot(i) end)
		hot.slots[i] = { Button = b, Stroke = st, Lift = lift, Inner = inner, Tint = tn, Sel = nil }
	end
	refs.HotEmpty.Visible = #items == 0
	UI.RefreshHotbar()
	task.defer(fitWallet)
	task.delay(0.15, fitWallet) -- again once the layout has settled
end

local function cycleRods(dir)
	local rods = {}
	for i, it in hot.items do if it.Kind == "Rod" then table.insert(rods, i) end end
	if #rods == 0 then return end
	local held = heldRodId()
	local cur = 0
	for k, i in rods do if hot.items[i].Id == held then cur = k end end
	local nxt = cur + dir
	if nxt > #rods then nxt = 0 elseif nxt < 0 then nxt = #rods end
	if nxt == 0 then
		local h = getHum()
		if h then h:UnequipTools() end
		showItemName("Hands free", C.Sub)
		task.defer(UI.RefreshHotbar)
	else
		selectSlot(rods[nxt])
	end
end

local KEYS = { [Enum.KeyCode.One] = 1, [Enum.KeyCode.Two] = 2, [Enum.KeyCode.Three] = 3, [Enum.KeyCode.Four] = 4, [Enum.KeyCode.Five] = 5,
	[Enum.KeyCode.Six] = 6, [Enum.KeyCode.Seven] = 7, [Enum.KeyCode.Eight] = 8, [Enum.KeyCode.Nine] = 9 }
UserInputService.InputBegan:Connect(function(input, gp)
	if UserInputService:GetFocusedTextBox() then return end
	local kc = input.KeyCode
	if KEYS[kc] and not gp then
		selectSlot(KEYS[kc])
	elseif kc == Enum.KeyCode.DPadRight or kc == Enum.KeyCode.ButtonR1 then
		if not GuiService.SelectedObject then cycleRods(1) end
	elseif kc == Enum.KeyCode.DPadLeft or kc == Enum.KeyCode.ButtonL1 then
		if not GuiService.SelectedObject then cycleRods(-1) end
	elseif kc == Enum.KeyCode.DPadUp and not GuiService.SelectedObject then
		for i, it in hot.items do if it.Kind == "Chum" then selectSlot(i) break end end
	elseif kc == Enum.KeyCode.DPadDown and not GuiService.SelectedObject then
		UI.TogglePicker("Bait", true)
	end
end)

local function watchChar(char)
	char.ChildAdded:Connect(function(c) if c:IsA("Tool") then task.defer(UI.RefreshHotbar) end end)
	char.ChildRemoved:Connect(function(c) if c:IsA("Tool") then task.defer(UI.RefreshHotbar) end end)
	task.defer(UI.RefreshHotbar)
end
player.CharacterAdded:Connect(watchChar)
if player.Character then watchChar(player.Character) end

-- hide Roblox's default hotbar / backpack (we draw our own)
task.spawn(function()
	for _ = 1, 30 do
		local ok = pcall(function() StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false) end)
		if ok then break end
		task.wait(0.5)
	end
end)

------------------------------------------------------------------ HUD
-- a dark pill with a thin accent outline (status / chum / meter / reel / picker / tutorial share it)
local function pill(parent, props, accent)
	local f = frame(parent, props, RADIUS, true)
	f.BackgroundColor3 = C.Panel
	f.BackgroundTransparency = 0.06
	local st = stroke(f, accent or C.Edge, 1.5, 0)
	return f, st
end

local function buildHUD()
	dim = make("Frame", { Name = "Dim", Position = UDim2.fromOffset(0, -200), Size = UDim2.new(1, 0, 1, 400), BackgroundColor3 = rgb(4, 5, 10), BackgroundTransparency = 1, BorderSizePixel = 0, ZIndex = 9, Active = false }, root)

	-- money + bag (bottom-right, big cream italic like the reference)
	local wallet = make("Frame", { AnchorPoint = Vector2.new(1, 1), Position = UDim2.new(1, -18, 1, -14), Size = UDim2.fromOffset(320, 74), BackgroundTransparency = 1 }, root)
	refs.BagText = title(wallet, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, 0, 0, 0), Size = UDim2.new(1, 0, 0, 26), TextSize = 22, Text = "0 / 150 fish",
		TextXAlignment = Enum.TextXAlignment.Right, TextColor3 = C.Cream, TextStrokeTransparency = 0.35 })
	refs.Money = title(wallet, { AnchorPoint = Vector2.new(1, 1), Position = UDim2.new(1, 0, 1, 0), Size = UDim2.new(1, 0, 0, 44), TextSize = 40, Text = "$0",
		TextXAlignment = Enum.TextXAlignment.Right, TextColor3 = C.Cream, TextStrokeTransparency = 0.25 })
	refs.MoneyScale = make("UIScale", {}, refs.Money)
	refs.Wallet = wallet

	-- left menu: outlined tiles (each its own accent)
	local menu = { { "Inventory", "🎒", "Bag", C.Orange }, { "Collection", "📖", "Index", C.Purple }, { "Guide", "❓", "Guide", C.Accent } }
	for i, m in menu do
		local b = button(root, { Position = UDim2.fromOffset(14, 14 + (i - 1) * 72), Size = UDim2.fromOffset(64, 64), BackgroundColor3 = m[4] }, function()
			if m[1] == "Guide" then UI.OpenTutorial(1) else togglePanel(m[1]) end
		end)
		text(b, { Size = UDim2.new(1, 0, 0, 30), Position = UDim2.fromOffset(0, 6), Text = m[2], TextSize = 24, TextXAlignment = Enum.TextXAlignment.Center, TextStrokeTransparency = 1, ZIndex = b.ZIndex + 1 })
		title(b, { Size = UDim2.new(1, 0, 0, 18), Position = UDim2.fromOffset(0, 40), Text = m[3], TextSize = 15, TextColor3 = m[4]:Lerp(WHITE, 0.25), TextXAlignment = Enum.TextXAlignment.Center, ZIndex = b.ZIndex + 1 })
	end

	-- status pill (top center)
	local status, sst = pill(root, { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 12), Size = UDim2.fromOffset(0, 36), AutomaticSize = Enum.AutomaticSize.X, Visible = false }, C.Accent)
	make("UIPadding", { PaddingLeft = UDim.new(0, 18), PaddingRight = UDim.new(0, 18) }, status)
	refs.StatusStroke = sst
	refs.Status = status
	refs.StatusText = title(status, { Size = UDim2.new(0, 0, 1, 0), AutomaticSize = Enum.AutomaticSize.X, TextSize = 18, TextXAlignment = Enum.TextXAlignment.Center })
	-- chum pill
	local chum, cst = pill(root, { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 54), Size = UDim2.fromOffset(0, 28), AutomaticSize = Enum.AutomaticSize.X, Visible = false }, C.Accent)
	make("UIPadding", { PaddingLeft = UDim.new(0, 14), PaddingRight = UDim.new(0, 14) }, chum)
	refs.ChumPill = chum
	refs.ChumStroke = cst
	refs.ChumText = text(chum, { Size = UDim2.new(0, 0, 1, 0), AutomaticSize = Enum.AutomaticSize.X, TextSize = 14, TextXAlignment = Enum.TextXAlignment.Center })

	-- toasts
	toastHolder = make("Frame", { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 96), Size = UDim2.fromOffset(600, 180), BackgroundTransparency = 1, ZIndex = 30 }, root)
	make("UIListLayout", { HorizontalAlignment = Enum.HorizontalAlignment.Center, Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder }, toastHolder)

	-- hotbar (bottom center): tile slots, then the bait tile
	local holder = make("Frame", { Name = "Hotbar", AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -12), Size = UDim2.fromOffset(0, SLOT), AutomaticSize = Enum.AutomaticSize.X, BackgroundTransparency = 1 }, root)
	make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, VerticalAlignment = Enum.VerticalAlignment.Bottom, Padding = UDim.new(0, 12), SortOrder = Enum.SortOrder.LayoutOrder }, holder)
	local slots = make("Frame", { BackgroundTransparency = 1, Size = UDim2.fromOffset(0, SLOT), AutomaticSize = Enum.AutomaticSize.X, LayoutOrder = 1 }, holder)
	make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, VerticalAlignment = Enum.VerticalAlignment.Center, Padding = UDim.new(0, 5), SortOrder = Enum.SortOrder.LayoutOrder }, slots)
	refs.HotSlots = slots
	refs.HotEmpty = text(slots, { Size = UDim2.fromOffset(150, SLOT), Text = "Loading gear...", TextColor3 = C.Sub, TextXAlignment = Enum.TextXAlignment.Center, LayoutOrder = 0 })
	-- bait tile
	local bait = button(holder, { Size = UDim2.fromOffset(180, SLOT), BackgroundColor3 = C.Green, LayoutOrder = 2 }, function() UI.TogglePicker("Bait") end)
	-- bait picture fills the left of the tile, faded, with the name over it
	local baitArtBox = make("Frame", { BackgroundTransparency = 1, Position = UDim2.fromOffset(2, 2), Size = UDim2.fromOffset(SLOT - 4, SLOT - 4), ZIndex = bait.ZIndex + 1 }, bait)
	refs.BaitArt = make("ImageLabel", { BackgroundTransparency = 1, Size = UDim2.fromScale(1, 1), ScaleType = Enum.ScaleType.Fit, ImageTransparency = 0.45, ZIndex = bait.ZIndex + 1 }, baitArtBox)
	refs.BaitIcon = text(baitArtBox, { Size = UDim2.fromScale(1, 1), TextSize = 26, TextXAlignment = Enum.TextXAlignment.Center, TextStrokeTransparency = 1, ZIndex = bait.ZIndex + 2 })
	refs.BaitName = title(bait, { Position = UDim2.fromOffset(58, 18), Size = UDim2.new(1, -64, 0, 20), TextSize = 18, ZIndex = bait.ZIndex + 3 })
	refs.BaitSub = text(bait, { Position = UDim2.fromOffset(58, 39), Size = UDim2.new(1, -64, 0, 16), TextSize = 13, TextColor3 = C.Sub, ZIndex = bait.ZIndex + 3 })
	title(bait, { Position = UDim2.fromOffset(6, 1), Size = UDim2.fromOffset(40, 14), Text = "BAIT", TextSize = 12, TextColor3 = C.Gold, ZIndex = bait.ZIndex + 1 })
	refs.Bar = holder
	refs.BarScale = make("UIScale", {}, holder)
	-- item name above the hotbar
	refs.ItemName = title(root, { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -(SLOT + 22)), Size = UDim2.fromOffset(560, 24), TextSize = 20, TextXAlignment = Enum.TextXAlignment.Center, TextTransparency = 1, TextStrokeTransparency = 1 })

	-- picker popup (bait)
	local picker = pill(root, { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -(SLOT + 26)), Size = UDim2.fromOffset(340, 0), AutomaticSize = Enum.AutomaticSize.Y, Visible = false, ZIndex = 20 }, C.Green)
	pad(picker, 8)
	make("UIListLayout", { Padding = UDim.new(0, 5), SortOrder = Enum.SortOrder.LayoutOrder }, picker)
	refs.Picker = picker

	-- cast meter
	local meter = pill(root, { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -(SLOT + 30)), Size = UDim2.fromOffset(300, 44), Visible = false }, C.Edge)
	local track = frame(meter, { Position = UDim2.fromOffset(12, 26), Size = UDim2.new(1, -24, 0, 8), BackgroundColor3 = C.Well }, 3, true)
	refs.MeterFill = frame(track, { Size = UDim2.fromScale(0, 1), BackgroundColor3 = WHITE }, 3, true)
	make("UIGradient", { Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, C.Green), ColorSequenceKeypoint.new(0.5, C.Gold), ColorSequenceKeypoint.new(1, C.Red) }) }, refs.MeterFill)
	refs.MeterText = title(meter, { Position = UDim2.fromOffset(12, 3), Size = UDim2.new(1, -24, 0, 20), TextSize = 16, TextXAlignment = Enum.TextXAlignment.Center })
	refs.Meter = meter

	-- reel minigame
	local reel, rst = pill(root, { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -22), Size = UDim2.fromOffset(500, 90), Visible = false }, C.Accent)
	refs.ReelStroke = rst
	refs.ReelTitle = title(reel, { Position = UDim2.fromOffset(14, 6), Size = UDim2.new(1, -28, 0, 20), TextSize = 16, TextXAlignment = Enum.TextXAlignment.Center })
	local rtrack = frame(reel, { Position = UDim2.fromOffset(14, 32), Size = UDim2.new(1, -28, 0, 28), BackgroundColor3 = C.Well }, RADIUS, true)
	stroke(rtrack, C.Edge, 1, 0)
	refs.ReelZone = frame(rtrack, { Size = UDim2.fromScale(0.3, 1), BackgroundColor3 = C.Green, BackgroundTransparency = 0.55 }, RADIUS, true)
	stroke(refs.ReelZone, C.Green, 1.5, 0)
	refs.ReelFish = text(rtrack, { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5), Size = UDim2.fromOffset(28, 28), Text = "🐟", TextSize = 22, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 3, TextStrokeTransparency = 1 })
	local ptrack = frame(reel, { Position = UDim2.fromOffset(14, 70), Size = UDim2.new(1, -28, 0, 8), BackgroundColor3 = C.Well }, 3, true)
	refs.ReelProgress = frame(ptrack, { Size = UDim2.fromScale(0.25, 1), BackgroundColor3 = C.Gold }, 3, true)
	refs.Reel = reel
	refs.ReelTrack = rtrack
end

------------------------------------------------------------------ catch card
-- compact catch notification: a dark tile that slides in at the right edge, glowing in the fish's rarity
local cardToken = 0
local catchCard
function UI.ShowCatch(info)
	cardToken += 1
	local token = cardToken
	local f = Config.FishById[info.Species]
	local rar = Config.RarityByName[f.Rarity]
	if catchCard then
		local old = catchCard
		tween(old, 0.2, { GroupTransparency = 1 })
		task.delay(0.22, function() old:Destroy() end)
	end
	local W, H = 290, 72
	local card = make("CanvasGroup", { AnchorPoint = Vector2.new(1, 0.5), Position = UDim2.new(1, W + 30, 0.42, 0), Size = UDim2.fromOffset(W, H),
		BackgroundColor3 = C.Panel, BorderSizePixel = 0, GroupTransparency = 1, ZIndex = 25 }, root)
	round(card, RADIUS)
	local st = stroke(card, rar.Color:Lerp(C.Edge, 0.25), 1.5, 0)
	tint(card, rar.Color, 0.35, 25)
	catchCard = card
	local vpBg = frame(card, { Position = UDim2.fromOffset(8, 8), Size = UDim2.fromOffset(60, 56), BackgroundColor3 = C.Well, ZIndex = 26 }, RADIUS, true)
	stroke(vpBg, rar.Color:Lerp(C.Edge, 0.5), 1, 0)
	local _, model = fishViewport(vpBg, info.Species, { Size = UDim2.fromScale(1, 1), ZIndex = 27 })
	title(card, { Position = UDim2.fromOffset(78, 6), Size = UDim2.new(1, -136, 0, 22), Text = (info.Giant and "\u{2B50} " or "") .. f.Name, TextSize = 19,
		TextColor3 = WHITE, TextTruncate = Enum.TextTruncate.AtEnd, ZIndex = 26 })
	local sub = rar.Name .. "  \u{2022}  " .. Config.FormatWeight(info.Weight) .. (info.Mutation and ("  \u{2022}  " .. info.Mutation) or "")
	title(card, { Position = UDim2.fromOffset(78, 28), Size = UDim2.new(1, -86, 0, 16), Text = sub, TextSize = 14, TextColor3 = rar.Color:Lerp(WHITE, 0.3), ZIndex = 26 })
	text(card, { Position = UDim2.fromOffset(78, 46), Size = UDim2.new(1, -86, 0, 16), Text = "\u{1F3B2} " .. Config.FormatOdds(info.Odds) .. "    " .. fmt(info.Value),
		TextSize = 13, TextColor3 = C.Gold, ZIndex = 26 })
	local badge = info.New and "NEW" or (info.Record and "BEST" or nil)
	if badge then
		local col = info.New and C.Green or C.Gold
		local bdg = frame(card, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -8, 0, 8), Size = UDim2.fromOffset(46, 20), BackgroundColor3 = C.Panel2, ZIndex = 27 }, RADIUS, true)
		stroke(bdg, col, 1.5, 0)
		title(bdg, { Size = UDim2.fromScale(1, 1), Text = badge, TextSize = 13, TextColor3 = col, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 28 })
	end
	tween(card, 0.4, { Position = UDim2.new(1, -14, 0.42, 0), GroupTransparency = 0 })
	local start = os.clock()
	local conn
	conn = RunService.RenderStepped:Connect(function()
		if token ~= cardToken or not card.Parent then conn:Disconnect() return end
		local t = os.clock() - start
		model:PivotTo(CFrame.Angles(0, math.sin(t * 1.4) * 0.45, 0) * CFrame.Angles(0, 0, math.sin(t * 6) * 0.04))
		if rar.Order >= 3 then st.Transparency = (math.sin(t * 4) + 1) * 0.25 end
	end)
	if rar.Order >= 5 then
		local glow = make("Frame", { AnchorPoint = Vector2.new(1, 0.5), Position = UDim2.new(1, 0, 0.42, 0), Size = UDim2.new(0, 440, 0, 260), BackgroundColor3 = rar.Color,
			BackgroundTransparency = 1, BorderSizePixel = 0, ZIndex = 5 }, root)
		make("UIGradient", { Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, 0.6) }) }, glow)
		tween(glow, 0.25, { BackgroundTransparency = 0.25 })
		task.delay(0.3, function() tween(glow, 1.2, { BackgroundTransparency = 1 }) task.wait(1.3) glow:Destroy() end)
	end
	task.delay(rar.Order >= 5 and 5 or 3.6, function()
		if token ~= cardToken or not card.Parent then return end
		tween(card, 0.5, { Position = UDim2.new(1, 40, 0.42, 0), GroupTransparency = 1 }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
		task.wait(0.52)
		if card.Parent then card:Destroy() end
		if catchCard == card then catchCard = nil end
	end)
end

------------------------------------------------------------------ status / meter / reel API
function UI.SetStatus(msg, color)
	if not msg then refs.Status.Visible = false return end
	local was = refs.Status.Visible
	refs.Status.Visible = true
	refs.StatusText.Text = msg
	refs.StatusText.TextColor3 = color or C.Text
	refs.StatusStroke.Color = color and color:Lerp(C.Edge, 0.35) or C.Edge
	if not was then
		local sc = refs.Status:FindFirstChild("Pop") or make("UIScale", { Name = "Pop" }, refs.Status)
		sc.Scale = 0.9
		tween(sc, 0.25, { Scale = 1 })
	end
end
function UI.SetChum(msg, color)
	if not msg then refs.ChumPill.Visible = false return end
	refs.ChumPill.Visible = true
	refs.ChumText.Text = msg
	refs.ChumStroke.Color = (color or C.Accent):Lerp(C.Edge, 0.35)
	refs.ChumText.TextColor3 = (color or C.Accent):Lerp(C.Text, 0.55)
end
function UI.ShowMeter(charge, dist, depthHint)
	if not charge then refs.Meter.Visible = false return end
	refs.Meter.Visible = true
	refs.MeterFill.Size = UDim2.fromScale(charge, 1)
	refs.MeterText.Text = string.format("Cast %dm%s", math.floor(dist), depthHint or "")
end
function UI.ShowReel(on, params)
	refs.Reel.Visible = on
	refs.Bar.Visible = not on
	refs.ItemName.Visible = not on
	if on then
		local col = rarityColor(params.Rarity)
		refs.ReelStroke.Color = col:Lerp(C.Edge, 0.25)
		refs.ReelTitle.Text = "Reel it in!  HOLD to push the green bar, let go to drift back"
		refs.ReelTitle.TextColor3 = col:Lerp(C.Text, 0.6)
		refs.ReelZone.Size = UDim2.fromScale(params.ZoneSize, 1)
		local sc = refs.Reel:FindFirstChild("Pop") or make("UIScale", { Name = "Pop" }, refs.Reel)
		sc.Scale = 0.92
		tween(sc, 0.25, { Scale = 1 })
	end
end
function UI.RenderReel(zonePos, zoneSize, fishPos, progress, inZone)
	refs.ReelZone.Position = UDim2.fromScale(zonePos, 0)
	refs.ReelZone.BackgroundTransparency = inZone and 0.45 or 0.75
	refs.ReelZone.UIStroke.Color = inZone and C.Green or C.Green:Lerp(C.Edge, 0.5)
	refs.ReelFish.Position = UDim2.fromScale(fishPos, 0.5)
	refs.ReelFish.Rotation = math.sin(os.clock() * 14) * 12
	refs.ReelProgress.Size = UDim2.fromScale(math.clamp(progress, 0, 1), 1)
	refs.ReelProgress.BackgroundColor3 = progress > 0.66 and C.Green or (progress > 0.33 and C.Gold or C.Red)
end

------------------------------------------------------------------ bait picker
local pickerKind
local function pickerRow(icon, titleText, sub, rightText, selected, onClick, color, artKey)
	local acc = selected and C.Gold or (color or C.Accent):Lerp(C.Edge, 0.35)
	local b = button(refs.Picker, { Size = UDim2.new(1, 0, 0, 46), BackgroundColor3 = acc, ZIndex = 21, Selectable = true }, onClick)
	setAccent(b, acc, selected)
	local box = make("Frame", { BackgroundTransparency = 1, Position = UDim2.fromOffset(4, 3), Size = UDim2.fromOffset(40, 40), ZIndex = 22 }, b)
	if not art(box, artKey, color, 22, 0.25, 1) then
		text(box, { Size = UDim2.fromScale(1, 1), Text = icon, TextSize = 22, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 22, TextStrokeTransparency = 1 })
	end
	title(b, { Position = UDim2.fromOffset(44, 5), Size = UDim2.new(1, -116, 0, 18), Text = titleText, TextSize = 16, TextColor3 = WHITE, ZIndex = 22 })
	text(b, { Position = UDim2.fromOffset(44, 24), Size = UDim2.new(1, -116, 0, 16), Text = sub, TextSize = 12, TextColor3 = C.Sub, ZIndex = 22 })
	title(b, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -10, 0, 0), Size = UDim2.fromOffset(70, 46), Text = rightText or "", TextSize = 16, TextXAlignment = Enum.TextXAlignment.Right, TextColor3 = C.Gold, ZIndex = 22 })
	return b
end

local function rebuildPicker()
	local p = refs.Picker
	for _, c in p:GetChildren() do if c:IsA("GuiObject") then c:Destroy() end end
	local d = UI.Data
	if not d or not pickerKind then return end
	title(p, { Size = UDim2.new(1, 0, 0, 22), Text = "Attach Bait", TextSize = 20, LayoutOrder = 0, ZIndex = 21 })
	text(p, { Size = UDim2.new(1, 0, 0, 14), Text = "One bait is used per cast", TextSize = 12, TextColor3 = C.Sub, LayoutOrder = 0, ZIndex = 21 })
	local first
	local none = pickerRow("⭕", "No bait", "Slower bites, no luck bonus", "", d.EquippedBait == nil, function()
		act("EquipBait", nil)
		UI.TogglePicker(nil)
	end)
	none.LayoutOrder = 1
	first = none
	local any = false
	for _, b in Config.Bait do
		local n = d.Bait[b.Id] or 0
		if n > 0 then
			any = true
			local row = pickerRow(b.Icon, b.Name, b.Desc, "x" .. n, d.EquippedBait == b.Id, function()
				act("EquipBait", b.Id)
				UI.TogglePicker(nil)
			end, b.Color, "Bait_" .. b.Id)
			row.LayoutOrder = 1 + b.Order
		end
	end
	if not any then text(p, { Size = UDim2.new(1, 0, 0, 20), Text = "Buy bait from Old Gill at the bait shop.", TextSize = 12, TextColor3 = C.Sub, LayoutOrder = 99, ZIndex = 21 }) end
	return first
end

function UI.TogglePicker(kind, fromGamepad)
	if kind == nil or pickerKind == kind or kind ~= "Bait" then
		pickerKind = nil
		refs.Picker.Visible = false
		if GuiService.SelectedObject and GuiService.SelectedObject:IsDescendantOf(refs.Picker) then GuiService.SelectedObject = nil end
		return
	end
	pickerKind = kind
	local first = rebuildPicker()
	refs.Picker.Visible = true
	local sc = refs.Picker:FindFirstChild("Pop") or make("UIScale", { Name = "Pop" }, refs.Picker)
	sc.Scale = 0.94
	tween(sc, 0.22, { Scale = 1 })
	if fromGamepad and first then GuiService.SelectedObject = first end
end

------------------------------------------------------------------ fish grid (bag + sell tab share it)
local SORTS = { { "Value", C.Green }, { "Weight", C.Accent }, { "Rarity", C.Purple }, { "Name", C.Gold } }
local sortBy = "Value"
local selectedUid

local function sortedFish(d)
	local fish = table.clone(d.Fish)
	table.sort(fish, function(a, b)
		if sortBy == "Weight" then return a.w > b.w end
		if sortBy == "Name" then
			local na, nb = Config.FishById[a.s].Name, Config.FishById[b.s].Name
			if na ~= nb then return na < nb end
			return a.v > b.v
		end
		if sortBy == "Rarity" then
			local ra, rb = Config.RarityByName[Config.FishById[a.s].Rarity].Order, Config.RarityByName[Config.FishById[b.s].Rarity].Order
			if ra ~= rb then return ra > rb end
		end
		return a.v > b.v
	end)
	return fish
end

-- one fish tile: name, weight, value; rarity glow from the bottom; star = giant, lock badge top-left
local function fishTile(parent, f, i, onPick, selected)
	local cfg = Config.FishById[f.s]
	local rar = Config.RarityByName[cfg.Rarity]
	local b = make("TextButton", { Name = "Fish_" .. f.u, AutoButtonColor = false, Text = "", BackgroundColor3 = selected and C.Panel3 or C.Panel2, BorderSizePixel = 0, LayoutOrder = i, ZIndex = 12 }, parent)
	round(b, RADIUS)
	local st = stroke(b, selected and WHITE or rar.Color:Lerp(C.Edge, 0.55), selected and 2 or 1.5, 0)
	tint(b, rar.Color, selected and 0.6 or 0.45, 12)
	if Config.IsGiant(cfg, f.w) then
		title(b, { AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, -1), Size = UDim2.fromOffset(20, 16), Text = "★", TextSize = 16, TextColor3 = C.Gold, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 14 })
	end
	if f.l then
		title(b, { Position = UDim2.fromOffset(5, 3), Size = UDim2.fromOffset(16, 16), Text = "🔒", TextSize = 12, ZIndex = 14, TextStrokeTransparency = 1 })
	end
	title(b, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -5, 0, 3), Size = UDim2.fromOffset(70, 15), Text = Config.FormatWeight(f.w), TextSize = 13, TextColor3 = C.Sub,
		TextXAlignment = Enum.TextXAlignment.Right, ZIndex = 14 })
	title(b, { AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.47), Size = UDim2.new(1, -10, 0, 40), Text = cfg.Name, TextSize = 17, TextWrapped = true,
		TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 14 })
	title(b, { AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -4), Size = UDim2.new(1, -8, 0, 16), Text = fmt(f.v), TextSize = 14, TextColor3 = C.Gold,
		TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 14 })
	local sc = make("UIScale", {}, b)
	b.MouseEnter:Connect(function() tween(sc, 0.14, { Scale = 1.04 }) tween(st, 0.14, { Thickness = 2 }) end)
	b.MouseLeave:Connect(function() tween(sc, 0.14, { Scale = 1 }) tween(st, 0.14, { Thickness = selected and 2 or 1.5 }) end)
	b.Activated:Connect(function() handlers.Click() onPick(f.u) end)
	return b
end

-- the selected fish's detail strip: 3D model, name, stats and its actions
local function detailBar(parent, d, sellMode)
	for _, c in parent:GetChildren() do if c:IsA("GuiObject") then c:Destroy() end end
	local f
	for _, x in d.Fish do if x.u == selectedUid then f = x end end
	if not f then
		title(parent, { Size = UDim2.fromScale(1, 1), Text = #d.Fish > 0 and "Select a fish to see it here" or "Caught fish show up here", TextSize = 17, TextColor3 = C.Sub,
			TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 13 })
		return
	end
	local cfg = Config.FishById[f.s]
	local rar = Config.RarityByName[cfg.Rarity]
	local vpBg = frame(parent, { Position = UDim2.fromOffset(6, 6), Size = UDim2.fromOffset(84, 58), BackgroundColor3 = C.Well, ZIndex = 13 }, RADIUS, true)
	stroke(vpBg, rar.Color:Lerp(C.Edge, 0.4), 1, 0)
	fishViewport(vpBg, f.s, { Size = UDim2.fromScale(1, 1), ZIndex = 14 })
	title(parent, { Position = UDim2.fromOffset(102, 6), Size = UDim2.fromOffset(300, 24), Text = cfg.Name .. (Config.IsGiant(cfg, f.w) and "  ★" or ""), TextSize = 22, ZIndex = 13 })
	title(parent, { Position = UDim2.fromOffset(102, 32), Size = UDim2.fromOffset(300, 16), Text = rar.Name .. "  •  " .. Config.FormatWeight(f.w) .. (f.m and ("  •  " .. f.m) or ""),
		TextSize = 15, TextColor3 = rar.Color:Lerp(WHITE, 0.3), ZIndex = 13 })
	title(parent, { Position = UDim2.fromOffset(102, 49), Size = UDim2.fromOffset(300, 16), Text = fmt(f.v), TextSize = 15, TextColor3 = C.Gold, ZIndex = 13 })
	local x = -8
	local function add(w, label, accent, fn, name)
		local bt = button(parent, { Name = name, AnchorPoint = Vector2.new(1, 0.5), Position = UDim2.new(1, x, 0.5, 0), Size = UDim2.fromOffset(w, 36), Text = label, TextSize = 17, ZIndex = 13, BackgroundColor3 = accent }, fn)
		x -= w + 8
		return bt
	end
	if sellMode then
		add(96, "Sell", f.l and C.Off or C.Gold, function()
			if f.l then UI.Notify("Unlock it first", C.Red) return end
			local r = act("SellFish", f.u)
			if r and r.ok then selectedUid = nil handlers.Sold(r.amount) end
		end)
	else
		local holding = d.Held == f.u
		add(96, holding and "Drop" or "Hold", holding and C.Orange or C.Accent, function()
			if holding then act("UnequipFish") else
				local r = act("EquipFish", f.u)
				if r and r.ok then closePanels() end
			end
		end, "HoldButton")
	end
	add(108, f.l and "🔒 Locked" or "🔓 Lock", f.l and C.Purple or C.Off, function() act("LockFish", f.u) end)
end

-- builds the shared "sort sidebar + grid + detail strip" layout into a container
local function fishBrowser(container, sellMode)
	local side = make("Frame", { Size = UDim2.new(0, 132, 1, 0), BackgroundTransparency = 1, ZIndex = 12 }, container)
	title(side, { Size = UDim2.new(1, 0, 0, 28), Text = "Sort By", TextSize = 22, ZIndex = 12 })
	make("Frame", { Position = UDim2.fromOffset(0, 30), Size = UDim2.new(1, -6, 0, 2), BackgroundColor3 = C.Edge, BorderSizePixel = 0, ZIndex = 12 }, side)
	local sortButtons = {}
	local grid, detail
	local api = {}
	for i, s in SORTS do
		sortButtons[s[1]] = button(side, { Position = UDim2.fromOffset(0, 40 + (i - 1) * 42), Size = UDim2.new(1, -6, 0, 34), Text = "  " .. s[1], TextSize = 18,
			TextXAlignment = Enum.TextXAlignment.Left, BackgroundColor3 = s[2], ZIndex = 13 }, function()
			sortBy = s[1]
			api.Refresh()
		end)
	end
	local w = well(container, { Position = UDim2.fromOffset(140, 0), Size = UDim2.new(1, -140, 1, -84), ZIndex = 11 })
	grid = scroller(w, { Position = UDim2.fromOffset(6, 6), Size = UDim2.new(1, -12, 1, -12) })
	local empty = title(w, { Size = UDim2.fromScale(1, 1), Text = sellMode and "Nothing to sell yet — go cast a line!" or "Your bag is empty — go cast a line!", TextSize = 22,
		TextColor3 = C.Sub, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 13, Visible = false })
	make("UIGridLayout", { CellSize = UDim2.fromOffset(134, 96), CellPadding = UDim2.fromOffset(6, 6), SortOrder = Enum.SortOrder.LayoutOrder }, grid)
	make("UIPadding", { PaddingTop = UDim.new(0, 3), PaddingLeft = UDim.new(0, 3), PaddingRight = UDim.new(0, 3), PaddingBottom = UDim.new(0, 3) }, grid)
	detail = tile(container, { Position = UDim2.new(0, 140, 1, -76), Size = UDim2.new(1, -140, 0, 70), BackgroundColor3 = C.Panel2, ZIndex = 12 }, nil)
	function api.Refresh()
		local d = UI.Data
		if not d then return end
		setTabs(sortButtons, sortBy)
		for _, c in grid:GetChildren() do if c:IsA("GuiObject") then c:Destroy() end end
		local list = sortedFish(d)
		local found = false
		for i, f in list do
			if i > 150 then break end
			if f.u == selectedUid then found = true end
			fishTile(grid, f, i, function(uid)
				selectedUid = uid
				api.Refresh()
			end, f.u == selectedUid)
		end
		if not found then selectedUid = nil end
		empty.Visible = #list == 0
		detailBar(detail, d, sellMode)
	end
	return api
end

------------------------------------------------------------------ shop (Old Gill)
local shopTab = "Rods"
local shopList, shopTabs, shopHeader, sellBrowser, sellAllBtn, shopSellPane
local TABS = { { "Rods", C.Accent }, { "Bait", C.Green }, { "Chum", C.Orange }, { "Sell", C.Gold } }

local function statBar(parent, y, label, value, maxV, color)
	title(parent, { Position = UDim2.fromOffset(0, y), Size = UDim2.fromOffset(78, 15), Text = label, TextSize = 13, TextColor3 = C.Sub, ZIndex = 14 })
	local tr = frame(parent, { Position = UDim2.fromOffset(80, y + 4), Size = UDim2.fromOffset(120, 6), BackgroundColor3 = C.Well, ZIndex = 14 }, 3, true)
	frame(tr, { Size = UDim2.fromScale(math.clamp(value / maxV, 0.04, 1), 1), BackgroundColor3 = color, ZIndex = 15 }, 3, true)
end

local function card(h, accent)
	return tile(shopList, { Size = UDim2.new(1, -8, 0, h), BackgroundColor3 = C.Panel2, ZIndex = 12 }, accent, 12)
end

local function rebuildShop()
	if not shopList then return end
	local d = UI.Data
	if not d then return end
	setTabs(shopTabs, shopTab)
	local selling = shopTab == "Sell"
	shopList.Parent.Visible = not selling
	shopSellPane.Visible = selling
	if selling then
		local total, n = 0, 0
		for _, f in d.Fish do if not f.l then total += f.v n += 1 end end
		shopHeader.Text = string.format("%d fish ready to sell  •  %s", n, fmt(total))
		sellAllBtn.Text = "Sell All  " .. fmt(total)
		setAccent(sellAllBtn, total > 0 and C.Gold or C.Off, total > 0)
		sellBrowser.Refresh()
		return
	end
	for _, c in shopList:GetChildren() do if c:IsA("GuiObject") then c:Destroy() end end
	if shopTab == "Rods" then
		local owned = 0
		for _, r in Config.Rods do if d.Rods[r.Id] then owned += 1 end end
		shopHeader.Text = string.format("%d / %d Rods Owned", owned, #Config.Rods)
		for _, r in Config.Rods do
			local tier = rodTier(r)
			local row = card(84, tier)
			row.LayoutOrder = r.Order
			local iconBg = tile(row, { Position = UDim2.fromOffset(10, 10), Size = UDim2.fromOffset(64, 64), BackgroundColor3 = C.Well, ZIndex = 13 }, tier, 13)
			art(iconBg, "Rod_" .. r.Id, tier, 14, 0.12, 0.96)
			title(row, { Position = UDim2.fromOffset(86, 8), Size = UDim2.fromOffset(240, 24), Text = r.Name, TextSize = 21, ZIndex = 13 })
			local stats = make("Frame", { Position = UDim2.fromOffset(86, 34), Size = UDim2.fromOffset(210, 46), BackgroundTransparency = 1, ZIndex = 13 }, row)
			statBar(stats, 0, "🍀 Luck x" .. r.Luck, r.Luck, 11, C.Green)
			statBar(stats, 15, "💪 Str x" .. r.Strength, r.Strength, 12, C.Orange)
			local zone = Config.RodZone(r)
			statBar(stats, 30, "🌊 " .. Config.ZoneLineDepth[zone] .. "m", zone, #Config.Zones, C.Accent)
			title(row, { Position = UDim2.fromOffset(310, 30), Size = UDim2.fromOffset(150, 36), Text = "Line depth\n" .. Config.Zones[zone].Name, TextSize = 15,
				TextColor3 = Config.Zones[zone].Color:Lerp(WHITE, 0.35), ZIndex = 13, TextYAlignment = Enum.TextYAlignment.Top })
			local own = d.Rods[r.Id]
			local equipped = d.EquippedRod == r.Id
			local label = own and (equipped and "Equipped" or "Equip") or fmt(r.Price)
			local accent = own and (equipped and C.Off or C.Accent) or (d.Money >= r.Price and C.Green or C.Off)
			button(row, { AnchorPoint = Vector2.new(1, 0.5), Position = UDim2.new(1, -12, 0.5, 0), Size = UDim2.fromOffset(130, 40), Text = label, TextSize = 18, ZIndex = 13,
				BackgroundColor3 = accent }, function()
				if own then act("EquipRod", r.Id) else act("BuyRod", r.Id) end
			end)
		end
	elseif shopTab == "Bait" or shopTab == "Chum" then
		local list = shopTab == "Bait" and Config.Bait or Config.Chum
		local qtys = shopTab == "Bait" and { 1, 10, 25 } or { 1, 5 }
		shopHeader.Text = shopTab == "Bait" and "Bait boosts luck and bite speed" or "Chum boosts every line in its ring"
		for _, it in list do
			local row = card(68, it.Color)
			row.LayoutOrder = it.Order
			local ib = tile(row, { Position = UDim2.fromOffset(10, 9), Size = UDim2.fromOffset(50, 50), BackgroundColor3 = C.Well, ZIndex = 13 }, it.Color, 13)
			if not art(ib, (shopTab == "Bait" and "Bait_" or "Chum_") .. it.Id, it.Color, 14, 0.12, 0.96) then
				text(ib, { Size = UDim2.fromScale(1, 1), Text = it.Icon, TextSize = 26, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 14, TextStrokeTransparency = 1 })
			end
			title(row, { Position = UDim2.fromOffset(72, 9), Size = UDim2.fromOffset(300, 22), Text = it.Name .. "   " .. fmt(it.Price), TextSize = 19, ZIndex = 13 })
			local owned = (shopTab == "Bait" and d.Bait or d.Chum)[it.Id] or 0
			text(row, { Position = UDim2.fromOffset(72, 34), Size = UDim2.fromOffset(330, 18), Text = it.Desc .. (it.Duration and (" • " .. it.Duration .. "s") or "") .. "   (own " .. owned .. ")",
				TextSize = 13, TextColor3 = C.Sub, ZIndex = 13 })
			for i, q in qtys do
				local cost = it.Price * q
				button(row, { AnchorPoint = Vector2.new(1, 0.5), Position = UDim2.new(1, -12 - (#qtys - i) * 80, 0.5, 0), Size = UDim2.fromOffset(72, 38), Text = "x" .. q, TextSize = 18, ZIndex = 13,
					BackgroundColor3 = d.Money >= cost and C.Green or C.Off }, function()
					act(shopTab == "Bait" and "BuyBait" or "BuyChum", it.Id, q)
				end)
			end
		end
	end
end

-- kept for compatibility: fish rows now render as the shared tile grid
function UI.FishRows(list, sellMode)
	local d = UI.Data
	for i, f in sortedFish(d) do
		if i > 150 then break end
		fishTile(list, f, i, function(uid) selectedUid = uid end, false)
	end
end

local function buildShop()
	local p, body = makePanel("Shop", "Old Gill's Tackle", C.Orange)
	shopTabs = tabRow(p, TABS, function(name)
		shopTab = name
		selectedUid = nil
		rebuildShop()
	end, 296, 18)
	local tut = button(body, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, 0, 0, -2), Size = UDim2.fromOffset(110, 30), Text = "Tutorial", TextSize = 17, ZIndex = 13, BackgroundColor3 = C.Purple }, function()
		UI.OpenTutorial(1)
	end)
	tut.Name = "Tutorial"
	shopHeader = title(body, { Size = UDim2.new(1, 0, 0, 26), TextSize = 22, TextColor3 = C.Gold, ZIndex = 12 })
	local w = well(body, { Position = UDim2.fromOffset(0, 32), Size = UDim2.new(1, 0, 1, -32), ZIndex = 11 })
	shopList = scroller(w, { Position = UDim2.fromOffset(6, 6), Size = UDim2.new(1, -12, 1, -12) })
	make("UIListLayout", { Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder }, shopList)
	make("UIPadding", { PaddingTop = UDim.new(0, 3), PaddingLeft = UDim.new(0, 3) }, shopList)
	-- sell tab: the same fish browser as the bag, plus a Sell All button
	shopSellPane = make("Frame", { Position = UDim2.fromOffset(0, 32), Size = UDim2.new(1, 0, 1, -32), BackgroundTransparency = 1, Visible = false, ZIndex = 11 }, body)
	sellBrowser = fishBrowser(shopSellPane, true)
	sellAllBtn = button(body, { AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, 0, 0, -2), Size = UDim2.fromOffset(190, 30), Text = "Sell All", TextSize = 17, ZIndex = 13, BackgroundColor3 = C.Gold }, function()
		local r = act("SellAll")
		if r and r.ok then selectedUid = nil handlers.Sold(r.amount) end
	end)
	shopSellPane:GetPropertyChangedSignal("Visible"):Connect(function() sellAllBtn.Visible = shopSellPane.Visible tut.Visible = not shopSellPane.Visible end)
	sellAllBtn.Visible = false
end

function UI.OpenShop()
	showPanel("Shop")
	rebuildShop()
end

------------------------------------------------------------------ inventory (fish bag)
local invBrowser, invHeader
local function buildInventory()
	local p, body = makePanel("Inventory", "Fish Bag", C.Orange)
	invHeader = title(body, { Size = UDim2.new(1, 0, 0, 26), TextSize = 22, TextColor3 = C.Gold, ZIndex = 12 })
	local pane = make("Frame", { Position = UDim2.fromOffset(0, 32), Size = UDim2.new(1, 0, 1, -32), BackgroundTransparency = 1, ZIndex = 11 }, body)
	invBrowser = fishBrowser(pane, false)
end
local function rebuildInventory()
	if not invBrowser then return end
	local d = UI.Data
	local total = 0
	for _, f in d.Fish do total += f.v end
	invHeader.Text = string.format("%d / %d Fish  •  Worth %s", #d.Fish, Config.InventoryCap, fmt(total))
	invBrowser.Refresh()
end

------------------------------------------------------------------ collection
local colGrid, colHeader, colCards = nil, nil, {}
local function buildCollection()
	local p, body = makePanel("Collection", "Fish Index", C.Purple)
	colHeader = title(body, { Size = UDim2.new(1, 0, 0, 26), TextSize = 22, TextColor3 = C.Gold, ZIndex = 12 })
	local w = well(body, { Position = UDim2.fromOffset(0, 32), Size = UDim2.new(1, 0, 1, -32), ZIndex = 11 })
	colGrid = scroller(w, { Position = UDim2.fromOffset(6, 6), Size = UDim2.new(1, -12, 1, -12) })
	make("UIGridLayout", { CellSize = UDim2.fromOffset(134, 132), CellPadding = UDim2.fromOffset(6, 6), SortOrder = Enum.SortOrder.LayoutOrder }, colGrid)
	make("UIPadding", { PaddingTop = UDim.new(0, 3), PaddingLeft = UDim.new(0, 3) }, colGrid)
end
local colBuiltState = {}
local function rebuildCollection()
	if not colGrid then return end
	local d = UI.Data
	local found = 0
	for _, f in Config.Fish do
		local idx = d.Index[f.Id]
		if idx then found += 1 end
		local key = idx and (idx.c .. "_" .. idx.w) or "none"
		if colBuiltState[f.Id] ~= key then
			colBuiltState[f.Id] = key
			if colCards[f.Id] then colCards[f.Id]:Destroy() end
			local rar = Config.RarityByName[f.Rarity]
			local c = tile(colGrid, { BackgroundColor3 = C.Panel2, LayoutOrder = f.Order, ZIndex = 12 }, idx and rar.Color or nil, 12)
			fishViewport(c, f.Id, { Position = UDim2.fromOffset(6, 20), Size = UDim2.new(1, -12, 0, 60), ZIndex = 13 }, not idx)
			title(c, { Position = UDim2.fromOffset(7, 3), Size = UDim2.new(1, -14, 0, 15), Text = rar.Name, TextSize = 14, TextColor3 = idx and rar.Color:Lerp(WHITE, 0.25) or C.Off, ZIndex = 13 })
			title(c, { Position = UDim2.fromOffset(7, 82), Size = UDim2.new(1, -14, 0, 20), Text = idx and f.Name or "???", TextSize = 17, ZIndex = 13, TextTruncate = Enum.TextTruncate.AtEnd,
				TextXAlignment = Enum.TextXAlignment.Center })
			text(c, { Position = UDim2.fromOffset(7, 102), Size = UDim2.new(1, -14, 0, 26), Text = idx and ("Best " .. Config.FormatWeight(idx.w) .. "  •  Caught " .. idx.c) or (Config.Zones[f.Zone].Name .. " or deeper"),
				TextSize = 12, TextColor3 = C.Sub, ZIndex = 13, TextWrapped = true, TextXAlignment = Enum.TextXAlignment.Center, TextYAlignment = Enum.TextYAlignment.Top })
			colCards[f.Id] = c
		end
	end
	colHeader.Text = string.format("Discovered %d / %d Species", found, #Config.Fish)
end

------------------------------------------------------------------ tutorial (Old Gill speaks)
local tutPage = 1
local function buildTutorial()
	local t = pill(root, { Name = "Tutorial", AnchorPoint = Vector2.new(0.5, 1), Position = UDim2.new(0.5, 0, 1, -(SLOT + 34)), Size = UDim2.fromOffset(560, 140), Visible = false, ZIndex = 40 }, C.Gold:Lerp(C.Edge, 0.35))
	tint(t, C.Gold, 0.12, 40)
	make("UIScale", { Name = "Pop" }, t)
	local face = tile(t, { Position = UDim2.fromOffset(14, 14), Size = UDim2.fromOffset(64, 64), BackgroundColor3 = C.Well, ZIndex = 41 }, C.Gold, 41)
	text(face, { Size = UDim2.fromScale(1, 1), Text = "🧔", TextSize = 36, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 42, TextStrokeTransparency = 1 })
	title(t, { Position = UDim2.fromOffset(8, 82), Size = UDim2.fromOffset(76, 18), Text = "Old Gill", TextSize = 16, TextColor3 = C.Gold, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 41 })
	refs.TutTitle = title(t, { Position = UDim2.fromOffset(92, 10), Size = UDim2.new(1, -106, 0, 26), TextSize = 23, ZIndex = 41 })
	refs.TutText = text(t, { Position = UDim2.fromOffset(92, 40), Size = UDim2.new(1, -106, 0, 54), TextSize = 16, TextWrapped = true, TextYAlignment = Enum.TextYAlignment.Top, TextColor3 = rgb(220, 226, 245), ZIndex = 41 })
	refs.TutPage = title(t, { Position = UDim2.fromOffset(92, 104), Size = UDim2.fromOffset(80, 24), TextSize = 16, TextColor3 = C.Sub, ZIndex = 41 })
	refs.TutBack = button(t, { AnchorPoint = Vector2.new(1, 1), Position = UDim2.new(1, -122, 1, -12), Size = UDim2.fromOffset(92, 34), Text = "Back", TextSize = 17, ZIndex = 41, BackgroundColor3 = C.Off }, function() UI.OpenTutorial(tutPage - 1) end)
	refs.TutNext = button(t, { AnchorPoint = Vector2.new(1, 1), Position = UDim2.new(1, -14, 1, -12), Size = UDim2.fromOffset(100, 34), Text = "Next", TextSize = 17, ZIndex = 41, BackgroundColor3 = C.Green }, function()
		if tutPage >= #Config.TutorialPages then
			tween(t.Pop, 0.14, { Scale = 0.95 }, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
			task.delay(0.14, function() t.Visible = false end)
			if UI.Data and not UI.Data.TutorialSeen then handlers.Action("TutorialDone") end
		else
			UI.OpenTutorial(tutPage + 1)
		end
	end)
	refs.Tutorial = t
end
function UI.OpenTutorial(page)
	closePanels()
	refs.TutHidden = false
	local t = refs.Tutorial
	tutPage = math.clamp(page, 1, #Config.TutorialPages)
	local pg = Config.TutorialPages[tutPage]
	refs.TutTitle.Text = pg.Title
	refs.TutText.Text = pg.Text
	refs.TutPage.Text = tutPage .. " / " .. #Config.TutorialPages
	refs.TutBack.Visible = tutPage > 1
	refs.TutNext.Text = tutPage >= #Config.TutorialPages and "Got it!" or "Next"
	if not t.Visible then
		t.Visible = true
		t.Pop.Scale = 0.94
		tween(t.Pop, 0.25, { Scale = 1 })
	end
end

------------------------------------------------------------------ screen fade (falling in the lake)
local fadeGui, fadeToken = nil, 0
function UI.Fade(toBlack)
	if not fadeGui then
		fadeGui = make("ScreenGui", { Name = "Fade", IgnoreGuiInset = true, DisplayOrder = 50, ResetOnSpawn = false }, player:WaitForChild("PlayerGui"))
		make("Frame", { Name = "Black", Size = UDim2.fromScale(1, 1), BackgroundColor3 = rgb(4, 6, 14), BackgroundTransparency = 1, BorderSizePixel = 0 }, fadeGui)
	end
	local f = fadeGui.Black
	fadeToken += 1
	local tk = fadeToken
	if toBlack then
		tween(f, 0.45, { BackgroundTransparency = 0 }, Enum.EasingStyle.Sine, Enum.EasingDirection.In)
		task.delay(3, function() if tk == fadeToken then UI.Fade(false) end end)
	else
		tween(f, 0.7, { BackgroundTransparency = 1 }, Enum.EasingStyle.Sine, Enum.EasingDirection.Out)
	end
end

------------------------------------------------------------------ public
function UI.Init(h)
	handlers = h
	gui = make("ScreenGui", { Name = "FishingUI", ResetOnSpawn = false, ZIndexBehavior = Enum.ZIndexBehavior.Sibling, IgnoreGuiInset = false }, player:WaitForChild("PlayerGui"))
	root = make("Frame", { Size = UDim2.fromScale(1, 1), BackgroundTransparency = 1 }, gui)
	scaleObj = make("UIScale", {}, root)
	local function rescale()
		local vp = workspace.CurrentCamera.ViewportSize
		local s = math.clamp(math.min(vp.X / 1280, vp.Y / 720) * 1.05, 0.6, 1.15)
		scaleObj.Scale = s
		root.Size = UDim2.fromScale(1 / s, 1 / s)
	end
	rescale()
	workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(function() rescale() task.defer(fitWallet) end)
	buildHUD()
	buildShop()
	buildInventory()
	buildCollection()
	buildTutorial()
end

local lastMoney
function UI.Update(d)
	UI.Data = d
	refs.Money.Text = fmt(d.Money)
	if lastMoney and d.Money ~= lastMoney then
		refs.MoneyScale.Scale = d.Money > lastMoney and 1.08 or 0.96
		tween(refs.MoneyScale, 0.3, { Scale = 1 })
	end
	lastMoney = d.Money
	local full = #d.Fish >= Config.InventoryCap
	refs.BagText.Text = string.format("%d / %d fish%s", #d.Fish, Config.InventoryCap, full and "  •  FULL" or "")
	refs.BagText.TextColor3 = full and C.Red or C.Cream
	local b = d.EquippedBait and Config.BaitById[d.EquippedBait]
	local baitArt = b and ICONS["Bait_" .. b.Id]
	refs.BaitArt.Image = baitArt and ("rbxassetid://" .. baitArt) or ""
	refs.BaitArt.ImageColor3 = b and b.Color:Lerp(WHITE, 0.5) or WHITE
	if b then
		refs.BaitIcon.Text = baitArt and "" or b.Icon
		refs.BaitName.Text = b.Name
		refs.BaitSub.Text = "x" .. (d.Bait[b.Id] or 0) .. "  •  +" .. math.floor(b.Luck * 100) .. "% luck"
	else
		refs.BaitIcon.Text = "⭕"
		refs.BaitName.Text = "No bait"
		refs.BaitSub.Text = "Tap to attach"
	end
	rebuildHotbar(d)
	task.defer(fitWallet)
	if refs.Picker.Visible then rebuildPicker() end
	if openPanel == "Shop" then rebuildShop()
	elseif openPanel == "Inventory" then rebuildInventory()
	elseif openPanel == "Collection" then rebuildCollection() end
end

return UI
