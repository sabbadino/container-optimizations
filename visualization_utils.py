def visualize_solution(container, boxes, perms_list, orient, x, y, z, solver, n):
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except ImportError:
        print("matplotlib is not installed. Skipping visualization.")
        import sys
        sys.exit(0)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Draw container as wireframe
    cx, cy, cz = container
    for s, e in [([0,0,0],[cx,0,0]), ([0,0,0],[0,cy,0]), ([0,0,0],[0,0,cz]),
                 ([cx,0,0],[cx,cy,0]), ([cx,0,0],[cx,0,cz]),
                 ([0,cy,0],[cx,cy,0]), ([0,cy,0],[0,cy,cz]),
                 ([0,0,cz],[cx,0,cz]), ([0,0,cz],[0,cy,cz]),
                 ([cx,cy,0],[cx,cy,cz]), ([cx,0,cz],[cx,cy,cz]), ([0,cy,cz],[cx,cy,cz])]:
        ax.plot3D(*zip(s, e), color="black", linewidth=0.5)

    # Draw each box as a colored solid
    import random
    colors = plt.cm.get_cmap('tab20', n)
    for i in range(n):
        xi = solver.Value(x[i])
        yi = solver.Value(y[i])
        zi = solver.Value(z[i])
        orient_val = [solver.Value(orient[i][k]) for k in range(len(orient[i]))]
        orient_idx = orient_val.index(1)
        l, w, h = perms_list[i][orient_idx]
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
        box = Poly3DCollection(faces, alpha=0.5, facecolor=colors(i), edgecolor='k')
        ax.add_collection3d(box)

        # Draw original axes after rotation using quivers
        center_x = xi + l / 2
        center_y = yi + w / 2
        center_z = zi + h / 2
        box_id = boxes[i].get('id', i+1)
        rotation_type = boxes[i].get('rotation', 'free')
        label = f"{box_id} (rot={rotation_type})"
        # try:
        #     import matplotlib.patheffects as path_effects
        #     ax.text(
        #         center_x, center_y, center_z + h/4,  # offset above center
        #         label,
        #         color='yellow',
        #         fontsize=10,
        #         ha='center',
        #         va='center',
        #         weight='bold',
        #         path_effects=[path_effects.withStroke(linewidth=2, foreground='black')]
        #     )
        # except ImportError:
        #     ax.text(center_x, center_y, center_z + h/4, label, color='yellow', fontsize=14, ha='center', va='center', weight='bold')

        perm = perms_list[i][orient_idx]
        l0, w0, h0 = boxes[i]['size']
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
    plt.title('3D Container Packing Solution')

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='r', lw=2, label='Original x-axis'),
        Line2D([0], [0], color='g', lw=2, label='Original y-axis'),
        Line2D([0], [0], color='b', lw=2, label='Original z-axis')
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    plt.show()
