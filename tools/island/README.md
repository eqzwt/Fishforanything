# Island map tools

- `kit.py` + `glb.py`: procedural mesh kit (buildings, docks, palms, jungle trees, rocks, sea stacks, coral, kelp, shipwreck, ruins, props).
  Writes one GLB (one node per prop+material, named `<Prop>__<Mat>`), uploaded as group Model asset 139787652473856.
- `tex.py`: tileable color + normal maps for the kit materials (`m_*`) and terrain MaterialVariants (`t_*`).
- `nightsky.py`: aurora night skybox. Roblox slot mapping (verified in-game): Ft=-Z, Bk=+Z, Lf=+X, Rt=-X, Up rotated (dir = (-v, 1, -u)).
- In Studio: `ServerStorage.MapTools.TerrainGen` sculpts the terrain, `ServerStorage.MapTools.MapBuild` places everything.
- The old map is kept in `ServerStorage.OldMap_Retro`, old scripts in `ServerStorage.ScriptBackups_PreIsland`.
