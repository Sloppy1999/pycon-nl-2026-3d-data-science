P = np.asarray(down.points)
x, y = P[:, 0], P[:, 1]
tid = x // 50 * 100 + y // 50
ground = np.zeros(len(P), bool)
for t in np.unique(tid):
    i = np.flatnonzero(tid == t)
    tile = down.select_by_index(i)
    _, inl = tile.segment_plane(
        0.3, 3, 1000)
    ground[i[inl]] = True
