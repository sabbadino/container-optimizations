def visualize_solution(time_taken, container, boxes, perms_list, placements, status_str=None):
    """Render a 3D visualization of the container and placed boxes.

    Args:
        time_taken: Solver time in seconds (float), used in the title.
        container: Container definition. Either:
            - size triple [L, W, H], or
            - dict with keys: 'size' = [L, W, H] and optional 'id'.
        boxes: List of box dicts (metadata; used for ids and original sizes).
        perms_list: List of allowed orientation dimension tuples per box.
        placements: List of dicts with keys 'position', 'orientation', 'size', etc. (as returned by run_inner).
        status_str: Optional solver status string for the title.
    Note: If container is a dict with an 'id', it will be shown in the title.

    Returns:
        matplotlib.pyplot (plt) with the plot configured; call plt.show() to display.
    """
    # Ensure a non-interactive backend under pytest/headless to avoid Tk errors.
    try:
        import os
        import matplotlib
        if os.environ.get("PYTEST_CURRENT_TEST"):
            try:
                matplotlib.use("Agg", force=True)
            except Exception:
                pass
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except ImportError:
        print("matplotlib is not installed. Skipping visualization.")
        import sys
        sys.exit(0)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Normalize container input and draw container as wireframe
    container_id_val = None
    if isinstance(container, dict):
        size = container.get('size')
        if size is None:
            raise ValueError("container dict must contain 'size' = [L, W, H]")
        container_id_val = container.get('id')
        cx, cy, cz = size
    else:
        cx, cy, cz = container
    for s, e in [([0,0,0],[cx,0,0]), ([0,0,0],[0,cy,0]), ([0,0,0],[0,0,cz]),
                 ([cx,0,0],[cx,cy,0]), ([cx,0,0],[cx,0,cz]),
                 ([0,cy,0],[cx,cy,0]), ([0,cy,0],[0,cy,cz]),
                 ([0,0,cz],[cx,0,cz]), ([0,0,cz],[0,cy,cz]),
                 ([cx,cy,0],[cx,cy,cz]), ([cx,0,cz],[cx,cy,cz]), ([0,cy,cz],[cx,cy,cz])]:
        ax.plot3D(*zip(s, e), color="black", linewidth=0.5)

    # Draw each box as a colored solid
    n_local = len(placements)
    # Use modern, non-deprecated colormap access. We don't rely on LUT sizing
    # to keep compatibility across Matplotlib versions.
    colors = plt.get_cmap('tab20')
    for i in range(n_local):
        placement = placements[i]
        xi, yi, zi = placement['position']
        orient_idx = placement['orientation']
        l, w, h = placement['size']
        # Vertices of the box
        verts = [
            [xi, yi, zi],
            [xi + l, yi, zi],
            [xi + l, yi + w, zi],
            [xi, yi + w, zi],
            [xi, yi, zi + h],
            [xi + l, yi, zi + h],
            [xi + l, yi + w, zi + h],
            [xi, yi + w, zi + h],
        ]
        faces = [
            [verts[0], verts[1], verts[2], verts[3]],
            [verts[4], verts[5], verts[6], verts[7]],
            [verts[0], verts[1], verts[5], verts[4]],
            [verts[2], verts[3], verts[7], verts[6]],
            [verts[1], verts[2], verts[6], verts[5]],
            [verts[4], verts[7], verts[3], verts[0]],
        ]
        box = Poly3DCollection(
            faces,
            alpha=0.5,
            facecolor=colors(i % colors.N),
            edgecolor='k'
        )
        ax.add_collection3d(box)

        # Draw original axes after rotation using quivers
        center_x = xi + l / 2
        center_y = yi + w / 2
        center_z = zi + h / 2
        perm = perms_list[i][orient_idx]
        orig_axes = []
        used = [False, False, False]
        for val in perm:
            if val == boxes[i]['size'][0] and not used[0]:
                orig_axes.append('x')
                used[0] = True
            elif val == boxes[i]['size'][1] and not used[1]:
                orig_axes.append('y')
                used[1] = True
            else:
                orig_axes.append('z')
                used[2] = True
        axes_vecs = [(l/2, 0, 0), (0, w/2, 0), (0, 0, h/2)]
        colors_axes = {'x': 'r', 'y': 'g', 'z': 'b'}
        for (dx, dy, dz), orig in zip(axes_vecs, orig_axes):
            ax.quiver(center_x, center_y, center_z, dx, dy, dz, color=colors_axes[orig], linewidth=0.8)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_xlim(0, cx)
    ax.set_ylim(0, cy)
    ax.set_zlim(0, cz)
    ax.set_box_aspect([cx, cy, cz])
    title = '3D Container Packing Solution'
    if container_id_val is not None:
        title += f' (Container Id: {container_id_val})'
    if status_str:
        title += f'\nSolver status: {status_str}'
    if time_taken:
        title += f'\nTime taken: {time_taken:.3f} seconds'
        
    plt.title(title)

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='r', lw=2, label='Original x-axis'),
        Line2D([0], [0], color='g', lw=2, label='Original y-axis'),
        Line2D([0], [0], color='b', lw=2, label='Original z-axis')
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    return plt
