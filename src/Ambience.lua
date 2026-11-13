--[[
	Ambience: the island's living atmosphere on each client.
	  - time of day: lighting, fog and water colour blended every frame from Shared.DayCycle
	  - aurora event (server sets workspace "Aurora"): flowing ribbons fade in/out, subtle shimmer on the sea
	  - crisp sea (Map.Sea): the old lake look - a clear blue sheet that bobs, shimmers between two blues,
	    with a drifting faceted sheen and little square sparkles (engine water underneath is only for
	    swimming / drowning / fishing and is drawn invisibly from above)
	  - living ocean: foam washing along the shorelines,
	    ripples around dock posts and little rings out on the water (engine waves + reflections underneath)
	  - underwater: tint/visibility that deepen with depth and follow the time of day, light shafts by day,
	    plankton, small fish schools near the reefs, breath bubbles
	  - drives the breath meter from the server's "Breath" / "Underwater" player attributes
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Water = require(Shared:WaitForChild("Water"))
local Assets = require(Shared:WaitForChild("VFXAssets"))
local DayCycle = require(Shared:WaitForChild("DayCycle"))
local FishModels = require(Shared:WaitForChild("FishModels"))
local UI = require(script.Parent:WaitForChild("ClientModules"):WaitForChild("UI"))

local player = Players.LocalPlayer
local rgb = Color3.fromRGB
local AURORA_TEX = "rbxassetid://123139453413509"
local SHAFT_TEX = "rbxassetid://119161931038820"
local WL = Config.WaterLevel
local TERRAIN = workspace.Terrain
local rng = Random.new()

local holder = Instance.new("Folder")
holder.Name = "Ambience"
holder.Parent = workspace
local function anchorPart(name, size)
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true p.CanCollide = false p.CanQuery = false p.CanTouch = false p.CastShadow = false
	p.Transparency = 1
	p.Size = size or Vector3.new(1, 1, 1)
	p.Parent = holder
	return p
end
local function ns(...) -- quick NumberSequence from pairs
	local t, a = {}, { ... }
	for i = 1, #a, 2 do table.insert(t, NumberSequenceKeypoint.new(a[i], a[i + 1])) end
	return NumberSequence.new(t)
end

------------------------------------------------------------------ aurora ribbons (sky) + shimmer (sea)
local rig = anchorPart("AuroraRig")
local seaRig = anchorPart("AuroraSeaRig")
local ribbons = {}
local function ribbon(azFrom, azTo, radius, height, width, colors, alpha, speed, seed)
	local function ring(az)
		return Vector3.new(math.sin(az) * radius, height, -math.cos(az) * radius), Vector3.new(math.cos(az), 0, math.sin(az))
	end
	local p0, t0 = ring(azFrom)
	local p1, t1 = ring(azTo)
	local a0 = Instance.new("Attachment") a0.CFrame = CFrame.fromMatrix(p0, t0, Vector3.yAxis) a0.Parent = rig
	local a1 = Instance.new("Attachment") a1.CFrame = CFrame.fromMatrix(p1, t1, Vector3.yAxis) a1.Parent = rig
	local c = 4 / 3 * math.tan(math.abs(azTo - azFrom) / 4) * radius
	local b = Instance.new("Beam")
	b.Attachment0 = a0 b.Attachment1 = a1
	b.FaceCamera = false
	b.Texture = AURORA_TEX b.TextureMode = Enum.TextureMode.Wrap b.TextureLength = 260 b.TextureSpeed = speed
	b.LightEmission = 1 b.LightInfluence = 0 b.Brightness = 1.4
	b.Width0 = width b.Width1 = width b.Segments = 80
	b.CurveSize0 = c b.CurveSize1 = c
	b.Color = colors
	b.Enabled = false
	b.Parent = rig
	table.insert(ribbons, { beam = b, a0 = a0, a1 = a1, p0 = p0, p1 = p1, c = c, phase = seed, alpha = alpha })
end
local GREEN = ColorSequence.new({ ColorSequenceKeypoint.new(0, rgb(70, 255, 170)), ColorSequenceKeypoint.new(0.5, rgb(90, 240, 220)), ColorSequenceKeypoint.new(1, rgb(80, 255, 160)) })
local VIOLET = ColorSequence.new({ ColorSequenceKeypoint.new(0, rgb(150, 100, 255)), ColorSequenceKeypoint.new(0.5, rgb(90, 200, 255)), ColorSequenceKeypoint.new(1, rgb(170, 110, 255)) })
ribbon(math.rad(-75), math.rad(65), 780, 470, 300, GREEN, 0.42, 0.03, 1)
ribbon(math.rad(-35), math.rad(105), 840, 610, 240, VIOLET, 0.55, -0.022, 4)
ribbon(math.rad(150), math.rad(245), 800, 520, 220, GREEN, 0.5, 0.026, 7)
-- soft green shimmer lying on the sea toward the aurora (its reflection)
local shimmer = {}
for i, d in { { -70, 120 }, { -170, 160 } } do
	local a0 = Instance.new("Attachment") a0.CFrame = CFrame.fromMatrix(Vector3.new(-d[2], 0, d[1]), Vector3.xAxis, Vector3.zAxis) a0.Parent = seaRig
	local a1 = Instance.new("Attachment") a1.CFrame = CFrame.fromMatrix(Vector3.new(d[2], 0, d[1]), Vector3.xAxis, Vector3.zAxis) a1.Parent = seaRig
	local b = Instance.new("Beam")
	b.Attachment0 = a0 b.Attachment1 = a1 b.FaceCamera = false
	b.Texture = AURORA_TEX b.TextureMode = Enum.TextureMode.Wrap b.TextureLength = 70 b.TextureSpeed = 0.05 * (i == 1 and 1 or -1)
	b.LightEmission = 1 b.LightInfluence = 0 b.Width0 = 60 + i * 30 b.Width1 = 60 + i * 30 b.Segments = 20
	b.Color = i == 1 and GREEN or VIOLET
	b.Enabled = false
	b.Parent = seaRig
	table.insert(shimmer, b)
end

------------------------------------------------------------------ water mask (where the sea is, where the shore is) built once in the background
local GRID, MX0, MX1, MZ0, MZ1 = 8, -640, 640, -600, 640
local maskReady = false
local shore = {} -- shoreline points on the water side
local water = {} -- open water points (for glints / ripples)
task.spawn(function()
	local map = workspace:WaitForChild("Map", 60)
	local land = map and map:WaitForChild("Land", 60)
	if not land then return end
	task.wait(3)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = { land, TERRAIN }
	params.IgnoreWater = true
	local H = {}
	local n = 0
	for x = MX0, MX1, GRID do
		local col = {}
		for z = MZ0, MZ1, GRID do
			local hit = workspace:Raycast(Vector3.new(x, 200, z), Vector3.new(0, -400, 0), params)
			col[z] = hit and hit.Position.Y or -100
			n += 1
			if n % 600 == 0 then task.wait() end
		end
		H[x] = col
	end
	for x = MX0 + GRID, MX1 - GRID, GRID do
		for z = MZ0 + GRID, MZ1 - GRID, GRID do
			local h = H[x][z]
			if h < -0.6 then
				local nearLand = false
				for _, o in { { GRID, 0 }, { -GRID, 0 }, { 0, GRID }, { 0, -GRID } } do
					if H[x + o[1]][z + o[2]] > -0.2 then nearLand = true end
				end
				if nearLand then table.insert(shore, Vector3.new(x, WL + 0.12, z)) end
				if h < -3 then table.insert(water, Vector3.new(x, WL + 0.1, z)) end
			end
		end
	end
	maskReady = true
end)

-- dock posts (ripples): same rhythm the dock meshes were built with
local posts = {}
for z = -3, -93, -6 do table.insert(posts, Vector3.new(-4.1, WL + 0.1, 262 + z)) table.insert(posts, Vector3.new(4.1, WL + 0.1, 262 + z)) end
for _, x in { -13, -6.5, 6.5, 13 } do table.insert(posts, Vector3.new(x, WL + 0.1, 150)) end
for _, jx in { -96, 108 } do for z = -3, -45, -6 do table.insert(posts, Vector3.new(jx - 3.1, WL + 0.1, 262 + z)) table.insert(posts, Vector3.new(jx + 3.1, WL + 0.1, 262 + z)) end end

------------------------------------------------------------------ surface FX emitters (emit at chosen points)
local fxPart = anchorPart("SeaFX")
local fxAtt = Instance.new("Attachment") fxAtt.Parent = fxPart
local function emitter(props)
	local e = Instance.new("ParticleEmitter")
	e.Rate = 0
	e.LockedToPart = false
	for k, v in props do e[k] = v end
	e.Parent = fxAtt
	return e
end
-- sparkles: little square tiles that flash on the water (the old lake's glints, without studs)
local tiles, tileI = {}, 0
for i = 1, 60 do
	local g = Instance.new("Part")
	g.Name = "Glint"
	g.Anchored = true g.CanCollide = false g.CanQuery = false g.CanTouch = false g.CastShadow = false
	g.Material = Enum.Material.Plastic g.TopSurface = Enum.SurfaceType.Studs g.Transparency = 1 g.Size = Vector3.new(1, 0.12, 1)
	g.Parent = holder
	tiles[i] = { part = g, born = -100 }
end
local GLINT_LIFE = 1.4
local function glintTile(p, col)
	tileI = tileI % #tiles + 1
	local g = tiles[tileI]
	local sz = rng:NextInteger(1, 2)
	g.part.Size = Vector3.new(sz, 0.12, sz)
	g.part.CFrame = CFrame.new(math.floor(p.X) + 0.5, WL + 0.14, math.floor(p.Z) + 0.5)
	g.part.Color = col
	g.born = os.clock()
end
local foam = emitter({ Texture = Assets.Foam, LightInfluence = 1, Orientation = Enum.ParticleOrientation.VelocityPerpendicular,
	EmissionDirection = Enum.NormalId.Top, Speed = NumberRange.new(0.01), Lifetime = NumberRange.new(2.4, 3.6),
	Size = ns(0, 3, 1, 9), Transparency = ns(0, 1, 0.15, 0.45, 1, 1), Rotation = NumberRange.new(0, 360), RotSpeed = NumberRange.new(-8, 8) })
local ring = emitter({ Texture = Assets.ThinRing, LightInfluence = 0.6, Orientation = Enum.ParticleOrientation.VelocityPerpendicular,
	EmissionDirection = Enum.NormalId.Top, Speed = NumberRange.new(0.01), Lifetime = NumberRange.new(1.4, 2.2),
	Size = ns(0, 0.4, 1, 4.5), Transparency = ns(0, 0.35, 1, 1) })
local function emitAt(e, pos, n)
	fxAtt.WorldPosition = pos
	e:Emit(n or 1)
end

------------------------------------------------------------------ underwater
local cc = Instance.new("ColorCorrectionEffect") cc.Name = "Underwater" cc.Enabled = false cc.Parent = Lighting
local blur = Instance.new("BlurEffect") blur.Name = "UnderwaterBlur" blur.Size = 0 blur.Enabled = false blur.Parent = Lighting
local plankton = anchorPart("Plankton", Vector3.new(60, 30, 60))
local pe = Instance.new("ParticleEmitter")
pe.Texture = Assets.Mote pe.Color = ColorSequence.new(rgb(150, 230, 255)) pe.LightEmission = 1 pe.Brightness = 1.5
pe.Size = ns(0, 0, 0.3, 0.18, 1, 0) pe.Transparency = NumberSequence.new(0.2) pe.Lifetime = NumberRange.new(4, 7)
pe.Speed = NumberRange.new(0.2, 0.8) pe.SpreadAngle = Vector2.new(180, 180)
pe.Shape = Enum.ParticleEmitterShape.Box pe.ShapeStyle = Enum.ParticleEmitterShapeStyle.Volume pe.Rate = 0
pe.Parent = plankton
local diveLight = Instance.new("PointLight") diveLight.Color = rgb(130, 210, 255) diveLight.Range = 70 diveLight.Enabled = false diveLight.Parent = plankton
-- sun shafts reaching down from the surface (daytime)
local shafts = {}
local shaftRig = anchorPart("ShaftRig")
for i = 1, 6 do
	local a0 = Instance.new("Attachment") a0.Parent = shaftRig
	local a1 = Instance.new("Attachment") a1.Parent = shaftRig
	local b = Instance.new("Beam")
	b.Attachment0 = a0 b.Attachment1 = a1 b.FaceCamera = true
	b.Texture = SHAFT_TEX b.TextureMode = Enum.TextureMode.Stretch
	b.LightEmission = 0.8 b.LightInfluence = 0 b.Color = ColorSequence.new(rgb(180, 235, 255))
	b.Width0 = 7 b.Width1 = 16 b.Enabled = false
	b.Parent = shaftRig
	local ang = (i / 6) * math.pi * 2 + rng:NextNumber(-0.3, 0.3)
	table.insert(shafts, { beam = b, a0 = a0, a1 = a1, ang = ang, r = rng:NextNumber(12, 34), phase = rng:NextNumber(0, 6) })
end
-- breath bubbles from the player's head
local bubbles = Instance.new("ParticleEmitter")
bubbles.Texture = Assets.Bubble bubbles.Size = ns(0, 0.15, 1, 0.4) bubbles.Transparency = ns(0, 0.2, 1, 1)
bubbles.Lifetime = NumberRange.new(1.2, 2) bubbles.Speed = NumberRange.new(4, 7) bubbles.Acceleration = Vector3.new(0, 4, 0)
bubbles.SpreadAngle = Vector2.new(20, 20) bubbles.EmissionDirection = Enum.NormalId.Top bubbles.Rate = 0 bubbles.LightInfluence = 0.4
local function attachBubbles(char)
	local head = char:WaitForChild("Head", 10)
	if head then bubbles.Parent = head end
end
player.CharacterAdded:Connect(attachBubbles)
if player.Character then task.spawn(attachBubbles, player.Character) end

-- small fish schools circling the reefs (only animated when you're close)
local schools = {}
task.spawn(function()
	local map = workspace:WaitForChild("Map", 60)
	local under = map and map:WaitForChild("Underwater", 60)
	if not under then return end
	task.wait(4)
	local spots = {}
	for _, m in under:GetChildren() do
		if m.Name:find("^Coral") or m.Name:find("^Kelp") then table.insert(spots, m:GetPivot().Position) end
	end
	local species = { "Clownfish", "BlueTang", "Bluegill" }
	for i = 1, math.min(10, #spots) do
		local c = spots[math.floor((i - 1) * #spots / 10) + 1]
		local s = { center = c + Vector3.new(0, rng:NextNumber(3, 6), 0), radius = rng:NextNumber(5, 9), speed = rng:NextNumber(0.25, 0.4) * (rng:NextNumber() < 0.5 and -1 or 1), fish = {}, active = false, folder = Instance.new("Folder") }
		s.folder.Name = "School"
		for k = 1, 6 do
			local ok, f = pcall(function() return FishModels.Build(species[(i % 3) + 1], rng:NextNumber(0.9, 1.4)) end)
			if ok and f then
				for _, d in f:GetDescendants() do if d:IsA("BasePart") then d.Anchored = true d.CanCollide = false d.CanQuery = false d.CastShadow = false end end
				f.Parent = s.folder
				table.insert(s.fish, { model = f, off = Vector3.new(rng:NextNumber(-2.5, 2.5), rng:NextNumber(-1.5, 1.5), rng:NextNumber(-2.5, 2.5)), lag = k * 0.18 })
			end
		end
		table.insert(schools, s)
	end
end)

------------------------------------------------------------------ crisp sea surface (Map.Sea)
-- (parts can arrive late with streaming, so the lists are rebuilt whenever a piece shows up)
local seaTop, seaDeep, seaSheen = {}, {}, {}
local deepHidden = false
task.spawn(function()
	local map = workspace:WaitForChild("Map", 60)
	local sea = map and map:WaitForChild("Sea", 60)
	if not sea then return end
	local surf, deep, studs = sea:WaitForChild("Surface", 60), sea:WaitForChild("Deep", 60), sea:WaitForChild("StudSheen", 60)
	local function rebuild()
		local top = {}
		for _, p in surf:GetChildren() do
			if p:IsA("BasePart") then
				local cf = p:GetAttribute("BaseY") and (p.CFrame - Vector3.new(0, p.Position.Y - p:GetAttribute("BaseY"), 0)) or p.CFrame
				p:SetAttribute("BaseY", cf.Position.Y)
				table.insert(top, { part = p, cf = cf, t1 = p:FindFirstChild("Sheen1"), t2 = p:FindFirstChild("Sheen2") })
			end
		end
		local dp = {}
		for _, p in deep:GetChildren() do if p:IsA("BasePart") then p.Transparency = deepHidden and 1 or 0 table.insert(dp, p) end end
		local sh = {}
		if studs then
			for _, p in studs:GetChildren() do
				if p:IsA("BasePart") then
					local base = p:GetAttribute("BasePos") or p.Position
					p:SetAttribute("BasePos", base)
					table.insert(sh, { part = p, base = base })
				end
			end
		end
		seaTop, seaDeep, seaSheen = top, dp, sh
	end
	rebuild()
	for _, f in { surf, deep, studs } do
		f.ChildAdded:Connect(function() task.defer(rebuild) end)
		f.ChildRemoved:Connect(function() task.defer(rebuild) end)
	end
end)
local SEA_DAY, SEA_HI, SEA_NIGHT = rgb(45, 155, 235), rgb(80, 190, 250), rgb(34, 92, 170)
local DEEP_DAY, DEEP_NIGHT = rgb(28, 112, 196), rgb(16, 52, 116)
local SHEEN, SHEEN_AURORA = rgb(220, 245, 255), rgb(150, 255, 210)

------------------------------------------------------------------ main loop
local atmos = Lighting:FindFirstChildOfClass("Atmosphere")
local grade = Lighting:FindFirstChild("Grade")
local SHALLOW, DEEP = rgb(196, 228, 238), rgb(96, 136, 178)
local under, depthK, camWet, lastCheck = 0, 0, false, 0
local auroraK = 0
local glintAcc, foamAcc, ringAcc = 0, 0, 0

RunService.RenderStepped:Connect(function(dt)
	local cam = workspace.CurrentCamera
	local cp = cam.CFrame.Position
	local t = os.clock()

	-- time of day
	local h = DayCycle.Now()
	local v = DayCycle.Sample(h)
	local night = DayCycle.Night(h)
	local wantAurora = workspace:GetAttribute("Aurora") == true and night > 0.5
	auroraK += ((wantAurora and 1 or 0) - auroraK) * math.min(1, dt / 10) -- ~10s fades
	if not wantAurora and auroraK < 0.002 then auroraK = 0 end
	Lighting.ClockTime = h
	Lighting.Brightness = v.Brightness
	Lighting.ColorShift_Top = v.ShiftTop
	Lighting.ExposureCompensation = v.Exposure
	local amb, out = v.Ambient, v.Outdoor
	if auroraK > 0 then -- a faint green cast over the island while the aurora burns
		amb = amb:Lerp(rgb(46, 86, 86), 0.35 * auroraK)
		out = out:Lerp(rgb(70, 120, 118), 0.35 * auroraK)
	end
	if atmos then
		atmos.Color = auroraK > 0 and v.AtmColor:Lerp(rgb(50, 100, 100), 0.4 * auroraK) or v.AtmColor
		atmos.Decay = v.AtmDecay atmos.Density = v.Density atmos.Haze = v.Haze atmos.Glare = v.Glare
	end
	if grade then grade.TintColor = rgb(255, 255, 255):Lerp(rgb(226, 234, 255), night) end

	-- aurora ribbons + sea shimmer
	rig.CFrame = CFrame.new(cp)
	seaRig.CFrame = CFrame.new(cp.X, WL + 0.2, cp.Z)
	for _, r in ribbons do
		r.beam.Enabled = auroraK > 0
		if auroraK > 0 then
			r.beam.CurveSize0 = r.c * (1 + 0.22 * math.sin(t * 0.09 + r.phase))
			r.beam.CurveSize1 = r.c * (1 + 0.22 * math.cos(t * 0.07 + r.phase * 1.3))
			r.a0.Position = r.p0 + Vector3.new(0, math.sin(t * 0.05 + r.phase) * 50, 0)
			r.a1.Position = r.p1 + Vector3.new(0, math.cos(t * 0.06 + r.phase) * 50, 0)
			r.beam.Brightness = 2.2 + math.sin(t * 0.35 + r.phase) * 0.6
			local a = 1 - (1 - r.alpha) * auroraK
			r.beam.Transparency = ns(0, 1, 0.2, a, 0.5, a - 0.05 * auroraK, 0.8, a, 1, 1)
		end
	end
	for _, b in shimmer do
		b.Enabled = auroraK > 0 and cp.Y > WL
		if b.Enabled then
			local a = 1 - 0.2 * auroraK * (0.8 + 0.2 * math.sin(t * 0.7))
			b.Transparency = ns(0, 1, 0.25, a, 0.75, a, 1, 1)
		end
	end

	-- underwater?
	if t - lastCheck > 0.1 then
		lastCheck = t
		camWet = cp.Y < WL and Water.Submerged(cp)
	end
	local depth = math.max(0, WL - cp.Y)
	under += ((camWet and 1 or 0) - under) * math.min(1, dt * 6)
	depthK += (math.clamp(depth / 90, 0, 1) - depthK) * math.min(1, dt * 3)
	local day = 1 - night
	if camWet then
		-- clearer and brighter near the surface by day; darker and murkier as you dive (and at night)
		local col = rgb(52, 140, 176):Lerp(rgb(30, 80, 130), night):Lerp(rgb(12, 36, 84), depthK)
		TERRAIN.WaterColor = col
		TERRAIN.WaterTransparency = (0.9 - 0.08 * night) - 0.32 * depthK
	else
		TERRAIN.WaterColor = v.Water
		TERRAIN.WaterTransparency = 1 -- the crisp sea parts are the visible surface
	end
	if under > 0.01 then
		cc.Enabled = true blur.Enabled = true
		cc.TintColor = Color3.new(1, 1, 1):Lerp(SHALLOW:Lerp(DEEP, depthK), under)
		cc.Brightness = -(0.12 * depthK) * under
		cc.Saturation = -0.22 * under
		cc.Contrast = 0.06 * under
		blur.Size = (2 + 3 * depthK) * under
		local uw = rgb(120, 170, 210):Lerp(rgb(66, 96, 146), night):Lerp(rgb(36, 58, 104), depthK)
		amb = amb:Lerp(uw, under)
		out = out:Lerp(uw, under)
	else
		cc.Enabled = false blur.Enabled = false
	end
	Lighting.Ambient = amb
	Lighting.OutdoorAmbient = out
	plankton.CFrame = CFrame.new(cp)
	pe.Rate = camWet and 14 or 0
	diveLight.Enabled = under > 0.05
	diveLight.Brightness = (0.5 + 0.35 * night - 0.3 * depthK) * under
	-- light shafts by day near the surface
	shaftRig.CFrame = CFrame.new(cp.X, WL, cp.Z)
	local shaftK = under * day * (1 - math.clamp(depth / 45, 0, 1))
	for _, s in shafts do
		s.beam.Enabled = shaftK > 0.02
		if s.beam.Enabled then
			local a = s.ang + math.sin(t * 0.05 + s.phase) * 0.3
			local top = Vector3.new(math.cos(a) * s.r, -0.3, math.sin(a) * s.r)
			s.a0.Position = top
			s.a1.Position = top + Vector3.new(6, -38, 4)
			local tr = 1 - 0.32 * shaftK * (0.7 + 0.3 * math.sin(t * 0.6 + s.phase))
			s.beam.Transparency = ns(0, tr, 1, 1)
		end
	end

	-- the living surface (only when you're above it)
	if maskReady and cp.Y > WL - 1 then
		local sunDir = Lighting:GetSunDirection()
		local light = (sunDir.Y > -0.05) and sunDir or Lighting:GetMoonDirection()
		local flat = Vector3.new(light.X, 0, light.Z)
		flat = flat.Magnitude > 0.05 and flat.Unit or Vector3.new(0, 0, -1)
		local sideV = Vector3.new(-flat.Z, 0, flat.X)
		-- glints gather along the path of the sun / moon on the water
		local gcol = rgb(255, 255, 255):Lerp(rgb(255, 176, 120), math.clamp((h - 16.8) / 1.5, 0, 1) * (h < 19.5 and 1 or 0)):Lerp(rgb(170, 200, 255), night):Lerp(rgb(140, 255, 210), auroraK * 0.6)
		glintAcc += dt * (day * 16 + night * 6)
		while glintAcc >= 1 do
			glintAcc -= 1
			local d = rng:NextNumber(10, 110)
			local p = cp + flat * d + sideV * rng:NextNumber(-1, 1) * (6 + d * 0.28)
			p = Vector3.new(p.X, WL + 0.15, p.Z)
			if Water.InLake(p) then glintTile(p, gcol) end
		end
		-- foam washing up along the shore near you
		foam.Color = ColorSequence.new(rgb(255, 255, 255):Lerp(rgb(150, 170, 205), night))
		foamAcc += dt * 14
		local tries = 0
		while foamAcc >= 1 and tries < 40 do
			tries += 1
			local p = shore[rng:NextInteger(1, math.max(1, #shore))]
			if p and (p - cp).Magnitude < 170 then
				foamAcc -= 1
				emitAt(foam, p + Vector3.new(rng:NextNumber(-3, 3), 0, rng:NextNumber(-3, 3)))
			end
		end
		-- ripples around dock posts and here and there on open water
		ringAcc += dt * 4
		while ringAcc >= 1 do
			ringAcc -= 1
			local p
			if rng:NextNumber() < 0.6 then p = posts[rng:NextInteger(1, #posts)] else p = water[rng:NextInteger(1, math.max(1, #water))] end
			if p and (p - cp).Magnitude < 140 then emitAt(ring, p + Vector3.new(rng:NextNumber(-0.4, 0.4), 0, rng:NextNumber(-0.4, 0.4))) end
		end
	end

	-- crisp sea: gentle bob, colour shimmer, sliding sheen, square sparkles fading
	local bob = math.sin(t * 0.8) * 0.05
	local seaCol = SEA_DAY:Lerp(SEA_HI, (math.sin(t * 0.45) + 1) * 0.22):Lerp(SEA_NIGHT, night * 0.6)
	local sheenCol = SHEEN:Lerp(SHEEN_AURORA, auroraK * 0.6)
	for _, s in seaTop do
		s.part.CFrame = s.cf + Vector3.new(0, bob, 0)
		s.part.Color = seaCol
		if s.t1 then s.t1.OffsetStudsU = (t * 0.9) % 48 s.t1.OffsetStudsV = (t * 0.45) % 48 s.t1.Color3 = sheenCol end
		if s.t2 then s.t2.OffsetStudsU = (-t * 0.6) % 77 s.t2.OffsetStudsV = (t * 0.75) % 77 s.t2.Color3 = sheenCol end
	end
	-- the old lake trick: a faint studded sheet drifting over the studded surface, so the stud grids slide past each other
	local sx, sz = math.sin(t * 0.31) * 0.5, math.cos(t * 0.23) * 0.5
	local sheenT = 0.86 + math.sin(t * 0.7) * 0.03
	for _, s in seaSheen do
		s.part.Position = s.base + Vector3.new(sx, bob, sz)
		s.part.Transparency = sheenT
	end
	local deepCol = DEEP_DAY:Lerp(DEEP_NIGHT, night * 0.6)
	if camWet ~= deepHidden then
		deepHidden = camWet
		for _, p in seaDeep do p.Transparency = camWet and 1 or 0 end -- see the seabed while swimming
	end
	for _, p in seaDeep do p.Color = deepCol end
	for _, g in tiles do
		local age = t - g.born
		if age < GLINT_LIFE then
			local f = age < 0.5 and age / 0.5 or 1 - (age - 0.5) / (GLINT_LIFE - 0.5)
			g.part.Transparency = 1 - 0.75 * math.clamp(f, 0, 1)
		elseif g.part.Transparency < 1 then
			g.part.Transparency = 1
		end
	end

	-- fish schools near you
	for _, s in schools do
		local near = (s.center - cp).Magnitude < 130
		if near ~= s.active then
			s.active = near
			s.folder.Parent = near and holder or nil
		end
		if near then
			for _, f in s.fish do
				local a = (t - f.lag) * s.speed
				local p = s.center + Vector3.new(math.cos(a) * s.radius, math.sin(a * 2) * 0.8, math.sin(a) * s.radius) + f.off
				-- fish models face +Z, so look away from the travel direction
				local tangent = Vector3.new(-math.sin(a), 0, math.cos(a)) * math.sign(s.speed)
				f.model:PivotTo(CFrame.lookAt(p, p - tangent) * CFrame.Angles(0, math.sin(t * 6 + f.lag * 9) * 0.15, 0))
			end
		end
	end

	-- breath meter + bubbles
	local air = player:GetAttribute("Breath") or 100
	local isUnder = player:GetAttribute("Underwater") == true
	UI.SetBreath(air, isUnder or air < 99.5)
	bubbles.Rate = isUnder and (air < 25 and 6 or 1.5) or 0
end)
