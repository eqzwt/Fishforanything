--[[
	TerrainGen v2: smooth terrain is now only the sea floor + the water.
	The visible land is low-poly meshes (Map.Land) built from the SAME height function (landgen.py);
	this module mirrors it exactly (value noise on a fixed permutation table) so the sea floor meets the meshes.
	Under the land meshes the terrain is filled solid up to sea level so no water hides underneath.
]]
local Gen = {}
local RES = 4
Gen.X0, Gen.X1, Gen.Z0, Gen.Z1, Gen.Y0, Gen.Y1 = -896, 896, -896, 896, -112, 16
local band, floor, sqrt, clamp = bit32.band, math.floor, math.sqrt, math.clamp
local PERM = { 181,1,179,217,161,25,228,36,81,234,229,120,231,131,68,197,71,232,244,29,123,157,137,23,96,66,128,159,186,238,75,150,62,57,9,245,94,21,34,22,136,151,88,19,143,222,7,77,95,189,83,37,107,2,215,174,160,239,208,31,113,59,99,252,164,0,225,132,139,212,35,192,130,125,74,56,121,105,122,200,40,87,227,55,119,241,127,69,236,5,41,141,153,247,60,191,106,53,101,97,114,218,111,251,155,28,170,32,70,190,166,180,61,148,24,243,91,144,76,82,86,84,45,182,8,48,44,118,14,39,73,206,10,224,109,38,220,64,112,49,20,177,209,15,33,250,201,65,226,237,214,138,124,133,6,116,253,126,12,47,185,196,135,46,175,54,242,165,142,193,199,58,254,110,248,156,3,207,145,115,183,72,26,184,50,230,216,172,13,195,167,104,18,11,147,158,134,163,17,140,51,67,219,249,154,176,173,80,203,43,63,117,30,152,90,213,4,169,79,204,188,205,223,103,89,171,240,129,16,102,246,210,108,27,93,233,221,168,194,52,178,100,78,235,92,202,162,98,85,211,198,42,255,149,146,187 }
local P = table.create(512)
for i = 1, 256 do P[i] = PERM[i] P[i + 256] = PERM[i] end
local function ph(a) return P[band(a, 255) + 1] end
local function vnoise(x, z, s)
	local ix, iz = floor(x), floor(z)
	local fx, fz = x - ix, z - iz
	local u = fx * fx * (3 - 2 * fx)
	local v = fz * fz * (3 - 2 * fz)
	local function h(a, b) return ph(ph(a + s * 57) + b) end
	local a, b, c, d = h(ix, iz), h(ix + 1, iz), h(ix, iz + 1), h(ix + 1, iz + 1)
	local top = a + (b - a) * u
	local bot = c + (d - c) * u
	return (top + (bot - top) * v) / 255 - 0.5
end
local function fbm(x, z, oct, scale, seed)
	local amp, f, tot, norm = 1, 1 / scale, 0, 0
	for i = 1, oct do
		tot += amp * vnoise(x * f, z * f, seed + i)
		norm += amp
		amp *= 0.5
		f *= 2.03
	end
	return tot / norm
end
Gen.fbm = fbm
local function ss(a, b, x) local t = clamp((x - a) / (b - a), 0, 1) return t * t * (3 - 2 * t) end
local function lerp(a, b, t) return a + (b - a) * t end
local function chain(px, pz, pts)
	local best = 1e9
	for i = 1, #pts - 1 do
		local A, B = pts[i], pts[i + 1]
		local vx, vz = B[1] - A[1], B[2] - A[2]
		local t = clamp(((px - A[1]) * vx + (pz - A[2]) * vz) / (vx * vx + vz * vz), 0, 1)
		local qx, qz = A[1] + vx * t - px, A[2] + vz * t - pz
		local d = sqrt(qx * qx + qz * qz) - (A[3] + (B[3] - A[3]) * t)
		if d < best then best = d end
	end
	return best
end
local function ellipse(px, pz, cx, cz, rx, rz)
	local dx, dz = (px - cx) / rx, (pz - cz) / rz
	return (sqrt(dx * dx + dz * dz) - 1) * math.min(rx, rz)
end
local function circle(px, pz, cx, cz, r) return sqrt((px - cx) ^ 2 + (pz - cz) ^ 2) - r end
local function segd(px, pz, ax, az, bx, bz)
	local vx, vz = bx - ax, bz - az
	local t = clamp(((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz), 0, 1)
	local qx, qz = ax + vx * t - px, az + vz * t - pz
	return sqrt(qx * qx + qz * qz)
end
local function terrace(h, step, sharp)
	local k = h / step
	local fl = floor(k)
	return (fl + ss(1 - sharp, 1, k - fl)) * step
end
local WEST = { { -170, 285, 52 }, { -250, 190, 70 }, { -318, 70, 92 }, { -296, -60, 70 }, { -262, -150, 58 }, { -236, -228, 40 } }
local WEST2 = { { -205, -268, 22 }, { -160, -318, 12 } }
local EAST = { { 200, 290, 52 }, { 268, 205, 64 }, { 312, 110, 70 }, { 318, 35, 56 } }
local EASTISLES = { { 300, -65, 34 }, { 262, -150, 44 }, { 238, -210, 22 } }
local ROCKS = { { -170, 150, 13 }, { 205, 148, 11 }, { 78, -268, 15 }, { -48, -300, 10 }, { 340, -270, 26 }, { -360, -330, 30 } }
local PATHS = { { 0, 300, 0, 236 }, { 0, 292, 24, 262 }, { 24, 262, 46, 270 }, { 0, 300, -40, 268 }, { 0, 300, 40, 352 }, { 40, 352, 70, 420 } }
Gen.PATHS = PATHS

function Gen.Height(x, z)
	local n1 = fbm(x, z, 4, 90, 1)
	local n2 = fbm(x, z, 3, 26, 9)
	local r = sqrt((x - 8) ^ 2 + (z + 10) ^ 2)
	local fl = -24 - 18 * ss(30, 170, r) + n1 * 14 + n2 * 4
	fl = lerp(fl, -80 + n1 * 14, ss(330, 560, r))
	local h, kind = fl, 0
	local dt = segd(x, z, 125, -50, 40, -235) - (24 + n2 * 10)
	if dt < 22 then h = math.min(h, lerp(-96 + n2 * 6, h, ss(-6, 22, dt))) end
	local function land(d, top, slope, code)
		local v
		if d <= 0 then v = top(-d) else v = -d * slope end
		if v > h then h = v kind = code end
	end
	local dv = ellipse(x, z, 10, 332, 285, 97) + fbm(x, z, 2, 60, 21) * 18 * ss(60, 140, math.abs(x - 10))
	land(dv, function(i) return 0.6 + 3.8 * ss(2, 24, i) + (n2 * 2.4 + n1 * 3) * ss(30, 60, i) end, 0.2, 1)
	local dr = ellipse(x, z, 20, 478, 400, 120) + n1 * 30
	land(dr, function(i)
		local raw = 4.4 + 64 * ss(0, 85, i) * (0.75 + n1 * 1.4) + n2 * 6 * ss(0, 20, i)
		return lerp(raw, terrace(raw, 6.0, 0.35), 0.6 * ss(6, 14, raw))
	end, 0.5, 2)
	local dk = circle(x, z, 70, 425, 40) + n2 * 8
	land(dk, function(i) return lerp(6 + 22 * ss(0, 30, i), terrace(6 + 22 * ss(0, 30, i), 6.0, 0.3), 0.7) end, 0.6, 2)
	local dw = math.min(chain(x, z, WEST), chain(x, z, WEST2)) + n2 * 14 + n1 * 26
	local de = math.min(chain(x, z, EAST), chain(x, z, EASTISLES)) + n2 * 14 + n1 * 22
	local function cliffTop(i, seed)
		local H = 42 + 34 * fbm(x, z, 3, 70, seed) * 2
		local raw = 2.5 + H * ss(5, 24, i) + 3 * ss(24, 60, i) * n2
		return lerp(raw, terrace(raw, 8.0, 0.25), 0.9)
	end
	land(dw, function(i) return cliffTop(i, 31) end, 1.25, 3)
	land(de, function(i) return cliffTop(i, 47) end, 1.25, 3)
	land(circle(x, z, -118, -212, 27) + n2 * 6, function(i) return 0.6 + 3.2 * ss(0, 12, i) end, 0.45, 4)
	land(circle(x, z, 168, -252, 32) + n2 * 8, function(i) local raw = 2 + 30 * ss(4, 20, i) return lerp(raw, terrace(raw, 6.0, 0.3), 0.8) end, 1.1, 3)
	for _, rk in ROCKS do
		local rr = rk[3]
		land(circle(x, z, rk[1], rk[2], rr) + n2 * 6, function(i) local raw = 1.5 + rr * 1.1 * ss(2, rr * 0.7, i) return lerp(raw, terrace(raw, 5.0, 0.3), 0.8) end, 1.3, 3)
	end
	local dc = circle(x, z, -268, -40, 30) + n2 * 5
	if dc < 0 then h = math.min(h, lerp(-14, h, ss(-30, 0, dc))) kind = 0 end
	local gap = segd(x, z, -268, -40, -205, -52) - (8 + n2 * 6)
	if gap < 0 then h = math.min(h, -10) kind = 0 end
	local pd = 1e9
	for _, p in PATHS do pd = math.min(pd, segd(x, z, p[1], p[2], p[3], p[4])) end
	if pd < 5 and h > 2 and kind <= 2 then h = lerp(h, h - 0.35, ss(5, 2, pd)) end
	return h, kind
end

-- terrain top: the real floor in open water; tucked 1.5 under the meshes in the shallow band; sea level under land
local CUT = -4.5
function Gen.TerrainTop(x, z)
	local h = Gen.Height(x, z)
	if h < CUT - 3 then return h end
	return math.min(h - 1.5 * ss(CUT - 3, CUT, h), 0)
end

local M = Enum.Material
local function floorMat(x, z, h, slope)
	local n = fbm(x, z, 2, 18, 77)
	if slope > 1.0 then return (n > 0 and M.Basalt or M.Rock) end
	if h > -10 then return M.Sand end
	if h > -16 then return (n > 0.06 and M.Mud or M.Sand) end
	if h > -45 then return (n > 0.1 and M.Slate or M.Mud) end
	return (n > -0.03 and M.Slate or M.Mud)
end

function Gen.Band(i0, i1)
	local T = workspace.Terrain
	local CH = 64
	local ny = (Gen.Y1 - Gen.Y0) / RES
	for ci = i0, i1 do
		local z0 = Gen.Z0 + ci * CH
		for cj = 0, (Gen.X1 - Gen.X0) / CH - 1 do
			local x0 = Gen.X0 + cj * CH
			local n = CH / RES
			local H = {}
			for a = 0, n + 1 do
				H[a] = {}
				for b = 0, n + 1 do H[a][b] = Gen.TerrainTop(x0 + (a - 0.5) * RES, z0 + (b - 0.5) * RES) end
			end
			local mats, occ, liq = {}, {}, {}
			for a = 1, n do
				mats[a], occ[a], liq[a] = {}, {}, {}
				for yy = 1, ny do mats[a][yy], occ[a][yy], liq[a][yy] = {}, {}, {} end
				for b = 1, n do
					local h = H[a][b]
					local slope = math.max(math.abs(H[a + 1][b] - H[a - 1][b]), math.abs(H[a][b + 1] - H[a][b - 1])) / (2 * RES)
					local m = floorMat(x0 + (a - 0.5) * RES, z0 + (b - 0.5) * RES, h, slope)
					for yy = 1, ny do
						local yb = Gen.Y0 + (yy - 1) * RES
						local fill = clamp((h - yb) / RES, 0, 1)
						local water = (yb + RES <= 0) and 1 or 0
						mats[a][yy][b] = fill > 0 and m or M.Air
						occ[a][yy][b] = fill
						liq[a][yy][b] = water * (1 - fill)
					end
				end
			end
			T:WriteVoxelChannels(Region3.new(Vector3.new(x0, Gen.Y0, z0), Vector3.new(x0 + CH, Gen.Y1, z0 + CH)), RES, { SolidMaterial = mats, SolidOccupancy = occ, LiquidOccupancy = liq })
			task.wait()
		end
	end
end

return Gen
