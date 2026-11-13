--[[
	BrickLand: the island heightfield (TerrainGen2.Height) rebuilt as studded 8x8 brick columns,
	like the original lego map, in darker muted colours so it doesn't read as toys.
	  - land: 1-stud steps on meadows/paths/low ground, 2 on hills, 4 up high; ledges grass, risers rock
	  - seabed: bricks tinted by depth (wet sand -> teal -> blue -> navy) so the clear water shows depth
	  - columns reach 2 studs under their lowest neighbour (no gaps), merged up to 2x2 cells on land, 4x4/8x8 underwater
	Python twin: tools/meshkit/brickgen.py (preview). Usage: require(clone).Build(parentFolder), then .Stairs(land)
	(Studio copy: ServerStorage.MapTools.BrickLand; needs TerrainGen2 as a sibling, with Height returning h, kind, pd)
]]
local Gen = require(script.Parent.TerrainGen2)
local B = {}
local CELL, X0, X1, Z0, Z1 = 8, -504, 504, -376, 600
local NX, NZ = (X1 - X0) // CELL, (Z1 - Z0) // CELL
B.CELL, B.X0, B.Z0, B.NX, B.NZ = CELL, X0, Z0, NX, NZ
local rgb = Color3.fromRGB
B.PAL = {
	grass1 = rgb(70, 128, 70), grass2 = rgb(55, 110, 59), grass3 = rgb(86, 134, 70), grass4 = rgb(42, 93, 53), lime = rgb(116, 136, 66),
	sand = rgb(194, 174, 119), sand2 = rgb(189, 171, 123), sandwet = rgb(181, 157, 102), dirt = rgb(141, 105, 76), dirt2 = rgb(125, 92, 67),
	rock = rgb(124, 121, 115), rock2 = rgb(99, 96, 91), moss = rgb(81, 99, 72),
	sea1 = rgb(74, 149, 146), sea2 = rgb(50, 108, 141), sea3 = rgb(37, 74, 117), sea4 = rgb(27, 45, 83),
}

local function rnd(v) return math.floor(v + 0.5) end
local function quant(h, pd)
	if h >= 0 then
		local step = (pd < 5 or h < 10) and 1 or (h < 26 and 2 or 4)
		return math.max(rnd(h / step) * step, 1)
	end
	local step = h > -10 and 1 or (h > -30 and 2 or 4)
	return math.min(rnd(h / step) * step, -1)
end

-- top heights + colour names for every cell
function B.Grid()
	local top, K, PD, N = {}, {}, {}, {}
	for i = 1, NX do
		top[i], K[i], PD[i], N[i] = {}, {}, {}, {}
		local x = X0 + CELL / 2 + (i - 1) * CELL
		for j = 1, NZ do
			local z = Z0 + CELL / 2 + (j - 1) * CELL
			local h, k, pd = Gen.Height(x, z)
			top[i][j], K[i][j], PD[i][j], N[i][j] = quant(h, pd), k, pd, Gen.fbm(x, z, 2, 40, 77)
		end
		if i % 6 == 0 then task.wait() end
	end
	local function T(i, j) return top[math.clamp(i, 1, NX)][math.clamp(j, 1, NZ)] end
	local col, bottom = {}, {}
	for i = 1, NX do
		col[i], bottom[i] = {}, {}
		for j = 1, NZ do
			local t, k, pd, n = top[i][j], K[i][j], PD[i][j], N[i][j]
			local a, b, c, d = T(i + 1, j), T(i - 1, j), T(i, j + 1), T(i, j - 1)
			local nbmin, nbmax = math.min(a, b, c, d), math.max(a, b, c, d)
			local rise = nbmax - t
			local cn
			if t < 0 then
				cn = t >= -1 and "sandwet" or t >= -5 and "sea1" or t >= -15 and "sea2" or t >= -39 and "sea3" or "sea4"
			elseif ((k == 3 or k == 2) and rise >= 6) or (k == 3 and t <= 3) then
				cn = (n > 0 or t % 8 < 4) and "rock" or "rock2"
			elseif k == 3 then
				cn = n > 0.06 and "moss" or n > -0.06 and "grass4" or "grass2"
			elseif t <= 1 then
				cn = (i + j) % 3 ~= 0 and "sandwet" or "sand2"
			elseif t <= 2 and (k == 1 or k == 4) then
				cn = (i * 7 + j) % 4 ~= 0 and "sand" or "sand2"
			elseif pd < 3.5 and k <= 2 then
				cn = (i + j) % 2 == 1 and "dirt" or "dirt2"
			elseif k == 2 then
				cn = n < -0.08 and "grass4" or n < 0.08 and "grass2" or "grass1"
			else
				cn = n > 0.12 and "grass3" or n > 0.09 and "lime" or n > -0.06 and "grass1" or "grass2"
			end
			col[i][j] = cn
			bottom[i][j] = math.min(t, nbmin) - 2
		end
	end
	return top, col, bottom
end

-- top of the brick land at a world point (nil outside the grid)
function B.TopAt(top, x, z)
	local i, j = math.floor((x - X0) / CELL) + 1, math.floor((z - Z0) / CELL) + 1
	if i < 1 or j < 1 or i > NX or j > NZ then return nil end
	return top[i][j]
end

function B.Build(parent)
	local top, col, bottom = B.Grid()
	local used = {}
	for i = 1, NX do used[i] = {} end
	local count, chunk, chunkN = 0, nil, 0
	local function flush()
		if chunk then chunk.Parent = parent end
		chunkN += 1
		chunk = Instance.new("Folder")
		chunk.Name = "Bricks" .. chunkN
	end
	flush()
	for i = 1, NX do
		for j = 1, NZ do
			if not used[i][j] then
				local t, c = top[i][j], col[i][j]
				local lim = t > 0 and 2 or (t > -16 and 4 or 8)
				local w = 1
				while w < lim and i + w <= NX and not used[i + w][j] and top[i + w][j] == t and col[i + w][j] == c do w += 1 end
				local hh = 1
				while hh < lim and j + hh <= NZ do
					local ok = true
					for a = 0, w - 1 do
						if used[i + a][j + hh] or top[i + a][j + hh] ~= t or col[i + a][j + hh] ~= c then ok = false break end
					end
					if not ok then break end
					hh += 1
				end
				local b = math.huge
				for a = 0, w - 1 do
					for q = 0, hh - 1 do
						used[i + a][j + q] = true
						b = math.min(b, bottom[i + a][j + q])
					end
				end
				local p = Instance.new("Part")
				p.Name = t > 0 and "Brick" or "Bed"
				p.Anchored = true
				p.CanTouch = false
				p.Material = Enum.Material.Plastic
				p.TopSurface = Enum.SurfaceType.Studs
				p.BottomSurface = Enum.SurfaceType.Smooth
				p.Color = B.PAL[c]
				p.CastShadow = t > -16
				p.Size = Vector3.new(w * CELL, t - b, hh * CELL)
				p.Position = Vector3.new(X0 + (i - 1) * CELL + w * CELL / 2, (t + b) / 2, Z0 + (j - 1) * CELL + hh * CELL / 2)
				p.Parent = chunk
				count += 1
			end
		end
		if i % 4 == 0 then flush() task.wait() end
	end
	flush()
	return count, top
end

-- walkable brick staircases along the dirt paths: 1-stud risers every 2 studs, climbing early where the hill is steep
B.PATHS = { { 0, 300, 0, 236 }, { 0, 292, 24, 262 }, { 24, 262, 46, 270 }, { 0, 300, -40, 268 }, { 0, 300, 40, 352 }, { 40, 352, 70, 420 } }
function B.Stairs(land)
	local old = land:FindFirstChild("Stairs") if old then old:Destroy() end
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = { land }
	local function ground(x, z)
		local r = workspace:Raycast(Vector3.new(x, 300, z), Vector3.new(0, -600, 0), params)
		return r and r.Position.Y or 0
	end
	local folder = Instance.new("Folder")
	folder.Name = "Stairs"
	local STEP, WIDTH, made = 2, 6, 0
	for _, s in B.PATHS do
		local a, b = Vector3.new(s[1], 0, s[2]), Vector3.new(s[3], 0, s[4])
		local len = (b - a).Magnitude
		local dir = (b - a).Unit
		local n = math.floor(len / STEP)
		local g, h = {}, {}
		for i = 0, n do
			local p = a + dir * (i * STEP + STEP / 2)
			-- highest brick under the step's footprint (so the step never sits below the ground)
			local side = Vector3.new(-dir.Z, 0, dir.X)
			local top = -math.huge
			for _, o in { 0, -WIDTH / 2 + 0.3, WIDTH / 2 - 0.3 } do
				for _, f in { -STEP / 2 + 0.2, STEP / 2 - 0.2 } do
					local q = p + side * o + dir * f
					top = math.max(top, ground(q.X, q.Z))
				end
			end
			g[i] = top
			h[i] = top
		end
		local steep = false
		for i = 1, n do if math.abs(g[i] - g[i - 1]) > 1.01 then steep = true end end
		if steep then
			-- never more than 1 stud between neighbouring steps, in either direction
			for _ = 1, 2 do
				for i = n - 1, 0, -1 do h[i] = math.max(h[i], h[i + 1] - 1) end
				for i = 1, n do h[i] = math.max(h[i], h[i - 1] - 1) end
			end
			for i = 0, n do
				if h[i] > g[i] + 0.05 then
					local p = a + dir * (i * STEP + STEP / 2)
					local bottom = g[i] - 1.5
					local part = Instance.new("Part")
					part.Name = "Step"
					part.Anchored = true part.CanTouch = false
					part.Material = Enum.Material.Plastic
					part.TopSurface = Enum.SurfaceType.Studs part.BottomSurface = Enum.SurfaceType.Smooth
					part.Color = i % 2 == 0 and B.PAL.dirt or B.PAL.dirt2
					part.Size = Vector3.new(WIDTH, h[i] - bottom, STEP + 0.02)
					part.CFrame = CFrame.lookAt(Vector3.new(p.X, (h[i] + bottom) / 2, p.Z), Vector3.new(p.X, (h[i] + bottom) / 2, p.Z) + dir)
					part.Parent = folder
					made += 1
				end
			end
		end
	end
	folder.Parent = land
	return made
end

return B
