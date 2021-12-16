#!/bin/python3

import math
# from re import L
import numpy as np

import gmsh
import sys

from pathlib import Path
import shutil
import os
from tqdm import tqdm
import procrustes as pr

from typing import Union

import matplotlib.pyplot as plt


###########################   NN1   ###########################

def mesh_contour(coord: np.ndarray, mesh_file) -> np.ndarray:
    """Simple .mesh generation with Gmsh API from a given contour
    Returns the coordinates of inner vertices generated by GMSH

    :param np.ndarray coord: The coordinates of the contour
    :param string mesh_file: The name of the output .mesh file

    :return: Coordinates of inner vertices
    :rtype: np.ndarray
    """
    gmsh.initialize()

    # Print only gmsh warnings and errors
    gmsh.option.setNumber("General.Verbosity", 2)

    gmsh.model.add("polygon")

    # Number of vertices in contour
    nb_v_in_c = len(coord)

    # Constraint (h >> contour_lenght to avoid meshing (subdividing) of contours)
    h = 10

    # Vertices
    for i in range(nb_v_in_c):
        x = coord[i, 0]
        y = coord[i, 1]
        gmsh.model.geo.addPoint(x, y, 0, h, i)

    # Edges
    for i in range(nb_v_in_c):
        gmsh.model.geo.addLine(i, (i+1) % nb_v_in_c, i)

    gmsh.model.geo.addCurveLoop([i for i in range(nb_v_in_c)], 1)

    gmsh.model.geo.addPlaneSurface([1], 1)

    gmsh.model.geo.synchronize()

    # Meshing
    # gmsh.model.mesh.setAlgorithm(2, 1, 3) #Add non points
    gmsh.model.mesh.generate(2)

    # Coordinates of inner_vertices
    coord_inner_v = gmsh.model.mesh.getNodes()[1][len(
        coord)*3:]
   # Delete the third coordinates
    if len(coord_inner_v) > 0:
        coord_inner_v = np.delete(
            coord_inner_v, np.arange(-1, coord_inner_v.size, 3))

    gmsh.write(str(mesh_file))

    # # Open mesh in GUI
    if '-nopopup' not in sys.argv:
        gmsh.fltk.run()

    gmsh.model.remove()
    # gmsh.finalize()

    return coord_inner_v


def create_random_contour(nvert: int) -> np.ndarray:
    """Create a random polygonal contour with nvert vertices

    :param int nvert: The number of desired vertices

    :return: Vector of coordinates for the nvert vertices
    :rtype: np.ndarray
    """
    r = 1.
    rmin = 0.7
    theta = 0.
    x = y = 0.
    coord = np.ndarray((nvert, 2))

    for i in range(0, nvert):
        theta = (i + np.random.rand()) / nvert * 2 * math.pi
        r = np.random.rand() * (1 - rmin) + rmin
        x = r * math.cos(theta)
        y = r * math.sin(theta)

        coord[i, 0] = x
        coord[i, 1] = y

    return coord


def gen_database(Nc: int,  # Number of contour edges
                 # Dictionnary of requested polygons
                 # Request fomating dict({(ls,nb_of_polygons),(ls,nb_of_polygons)....})
                 requested_polygons: dict,
                 # Delete any previous files to start clean
                 # Data main folder
                 data_path: Path = Path("data"),
                 # Subfolders
                 meshes_folder: Path = Path("meshes"),
                 polygons_folder: Path = Path("polygons"),
                 # Label file
                 label_filename: Path = Path("labels"),
                 clean_data_dirs: bool = True) -> None:
    """Generates transformed contours and saves multiples output files
    Takes a dictionnary with numbers of requested polygons
    Request fomating : dict({(ls,nb_of_polygons),(ls,nb_of_polygons)....})


    Creates folders to store meshes and polygons
    Creates label file with two cols : filename, number of inner vertices
    Creates a file .dat for each polygon containing in one cols : (ls,x1,y1,x2,y2.....)^t
    Creates a file .mesh for each polygon generated by Gmsh

    Displays a simple progress bar with tqdm

    :param int Nc: Number of contour edges
    :param dict requested_polygons: Requested polygons
    :param Path data_path: main folder to store dataset
    :param Path meshes_folder: folder to store .mesh files
    :param Path polygons_folder:folder to store .dat files
    :param Path label_filename:Label file with
    :param bool clean_data_dirs: Delete any previous file and directories

    :return: Creates the output files in the desired folder
    :rtype:
    """
    print(f"Generating database for {Nc} vertices.")

    # Add polygons folder
    data_path = data_path / Path(str(Nc))

    # Delete any previous files to start clean
    if clean_data_dirs:
        shutil.rmtree(data_path, ignore_errors=True)

    # create tree
    try:
        os.makedirs(data_path)
    except FileExistsError:
        pass
    # data_path.mkdir(exist_ok=True)
    (data_path / polygons_folder).mkdir(exist_ok=True)
    (data_path / meshes_folder).mkdir(exist_ok=True)

    gmsh.initialize()

    # Create label file
    with open(data_path / label_filename, "w+") as label_file:
        # Header
        label_file.write("filename, N1\n")
        # Generate polygons, tqdm create a progress bar
        idx = 0
        for ls in sorted(requested_polygons.keys()):
            for _ in tqdm(range(requested_polygons[ls])):
                polygon_filename = Path(f"coord{ls}_{idx}.dat")

                # Creation of polygon
                coord = create_random_contour(Nc)
                # Normalisation
                pr.procrustes(coord)
                # Mesh polygon and get nb of inner vertices
                nb_inner_vert = len(mesh_contour(
                    coord, data_path / meshes_folder / polygon_filename.with_suffix(".mesh")))/2
                # Write label files
                label_file.write(f"{polygon_filename}, {nb_inner_vert}\n")

                # Write polygon file
                with open(data_path / polygons_folder / polygon_filename, "w+") as polygon_file:
                    polygon_file.write(str(ls)+"\n")
                    for i in coord:
                        polygon_file.write(str(i[0])+"\n")
                        polygon_file.write(str(i[1])+"\n")
                idx += 1
    gmsh.finalize()
    return


###########################   NN2   ###########################

def is_in_contour(x: float, y: float, coord: np.ndarray) -> bool:
    """Determine if the point is in the polygon

    :param float x: The x coordinates of point
    :param float y: The y coordinates of point

    :return: True if the point is inside the polynom, False otherwise
    :rtype: bool

    source : wikipedia
    """

    num = len(coord)
    j = num - 1
    c = False
    for i in range(num):
        if (x == coord[i][0]) and (y == coord[i][1]):
            # point is a corner
            return True
        if ((coord[i][1] > y) != (coord[j][1] > y)):
            slope = (x-coord[i][0])*(coord[j][1]-coord[i][1]) - \
                (coord[j][0]-coord[i][0])*(y-coord[i][1])
            if slope == 0:
                # point is on boundary
                return True
            if (slope < 0) != (coord[j][1] < coord[i][1]):
                c = not c
        j = i
    return c


def create_grid(coord: np.ndarray, ls: float) -> np.ndarray:
    """
    Creates uniform grided square arond the contour

    :param float ls: size of an edge inside the polygon

    :return: Coordinates of the grid
    :rtype: np.ndarray
    """
    # Grid scale factor
    Gscale_factor = 0.01  # 0.05 is enough -> 40*40 grid for ls = 1
    Gscale = Gscale_factor * ls  # size of mesh grid
    nnodes = int(2/Gscale)  # number of nodes on the grid side
    grid = np.empty((0, 2))
    x = -Gscale*nnodes/2  # On commence en bas a gauche du grid
    y = -Gscale*nnodes/2
    for i in range(nnodes):
        for j in range(nnodes):
            if is_in_contour(x, y, coord):
                grid = np.append(grid, [[x, y]], axis=0)  # NOT WORKING !!!!!

            x += Gscale
            # print(i,j)
            # print(grid[i+j,0],grid[i+j,1])
        x = -Gscale*nnodes/2
        y += Gscale
    return grid


def score_of_node(node: np.ndarray, nodes: np.ndarray) -> float:
    '''Gives the score of a grid node

    :param np.ndarray node: the grid node considered
    :param np.ndarray nodes: the coordinates of the inner vertices

    :return: score of the node
    :rtype: float
    '''
    nb_nodes = nodes.size//2  # number of inner vertices
    dist = np.zeros(nb_nodes)
    for i in range(0, nb_nodes):
        dist[i] = math.sqrt((node[0]-nodes[2*i])**2 +
                            (node[1]-nodes[2*i+1])**2)
    return min(dist)


def calculate_score_array(grid: np.ndarray, coord_inner_v: np.ndarray) -> np.ndarray:
    """Computes the scores of each grid node

    :param np.ndarray grid: the grid node over the polygon
    :param np.ndarray coord_inner_v: the coordinates of the inner vertices

    :return: scores of all grid nodes in a vector
    :rtype: np.ndarray
    """
    nb_nodes = (grid.size)//2
    Scores = np.zeros(nb_nodes)
    for i in range(nb_nodes):
        Scores[i] = score_of_node(
            np.array([grid[i, 0], grid[i, 1]]), coord_inner_v)
    return Scores


def place_inner_vertex(scores: np.array, grid: np.ndarray, ls: float) -> np.array:
    """Interpolates the position of the point given the scores on the grid

    :param np.ndarray scores: the scores of each point of the grid
    :param np.ndarray grid: the grid node over the polygon

    :return: coordinates of the point
    :rtype: list
    """

    coord_min_label = np.argmin(scores)

    # search for the 8 points around the minimum
    # /!\ Ne fonctionne pas si le minimum se trouve au bord,
    # /!\ ce qui est impossible si la taille de la grille est bien choisie
    # /!\ Si besoin de changer, définir un label de bord

    coord_min = grid[coord_min_label]

    Gscale = abs(coord_min[0]-grid[coord_min_label+1][0])

    local_domain_label = []
    local_domain_scores = []

    for i in range(len(grid)):
        if grid[i][0] == coord_min[0]:
            if abs(grid[i][1]-coord_min[1]) <= 1.1*Gscale:
                local_domain_label.append(i-1)
                local_domain_label.append(i)
                local_domain_label.append(i+1)

    # remove the center element to form the final local polygon
    del local_domain_label[4]

    local_domain_scores = [scores[i] for i in local_domain_label]

    # 0 1 2
    # 3   4
    # 5 6 7

    # print("local domain label = ", local_domain_label)
    # print("local domain scores = ", local_domain_scores)

    ###### INTERPOLATION ######
    # barycentric coordinates of the final point
    xs = [0, 1, 2, 5, 6, 7]
    ys = [0, 3, 5, 2, 4, 7]

    xsum = 0
    ysum = 0
    xsum_score = 0
    ysum_score = 0

    for i in xs:
        xsum += local_domain_scores[i]*grid[local_domain_label[i]][0]
        xsum_score += local_domain_scores[i]
    for i in ys:
        ysum += local_domain_scores[i]*grid[local_domain_label[i]][1]
        ysum_score += local_domain_scores[i]

    xbar = xsum/xsum_score  # optimal x position
    ybar = ysum/ysum_score  # optimal y position

    return [xbar, ybar]


def remove_points_grid(ls: float, vert: list, grid: np.ndarray, scores: np.array) -> np.ndarray:
    """Updates the grid and the scores by removing some non necessary points

    :param float ls: size of an edge inside the polygon
    :param list vert: coords of an inner vertex
    :param np.ndarray grid: the grid node over the polygon
    :param np.ndarray scores: the scores of each point of the grid

    :return: new grid and new scores
    :rtype: np.ndarray
    """
    x = vert[0]
    y = vert[1]
    radius = 0.1*ls  # ARBITRARY : MODIFY IF ERROR
    to_remove = []
    for i in range(len(grid)):
        # if the point is too close to the given coordinates
        if((grid[i][0]-x)**2 + (grid[i][1]-y)**2 < radius**2):
            to_remove.append(i)
    grid = np.delete(grid, to_remove, axis=0)
    scores = np.delete(scores, to_remove)
    return grid, scores


def compute_vertices(ls: float, contour: np.ndarray, grid: np.ndarray, scores: np.ndarray, nb_inner_v: int) -> np.ndarray:
    """Computes the coords of all the inner vertices

    :param float ls: size of an edge inside the polygon
    :param np.ndarray contour: coords of the contour
    :param np.ndarray grid: the grid node over the polygon
    :param np.ndarray scores: the scores of each point of the grid

    :return: out_vertices, the coords of all the inner vertices
    :rtype: np.ndarray
    """
    out_vertices = np.zeros((nb_inner_v, 2))  # coordinates of the vertices

    for i in range(nb_inner_v):  # A CORRIGER !!
        # print("lens = ", len(grid), len(scores))
        out_vertices[i] = place_inner_vertex(scores, grid, ls)
        grid, scores = remove_points_grid(ls, out_vertices[i], grid, scores)
        # remove grid points within a given radius of out_vertices[i]:

    print("out vertices : \n", out_vertices)

    return out_vertices


def main():
    # gmsh.initialize()
    # Test one mesh
    # coord = create_random_contour(10)
    # pr.procrustes(coord)
    # mesh_contour(coord, "out.msh")
    # gmsh.finalize()

    # Gen database
    # request fomating dict({(ls,nb_of_polygons),(ls,nb_of_polygons)....})

    # request = dict({(1.0, 1)})
    # gen_database(6, request)
    # request = dict({(1.0, 12000)})
    # gen_database(6, request)
    # request = dict({(1.0, 1)})
    # gen_database(8, request)
    # request = dict({(1.0, 48000)})
    # gen_database(10, request)
    # request = dict({(1.0, 95000)})
    # gen_database(12, request)
    # request = dict({(1.0, 190000)})
    # gen_database(14, request)
    # request = dict({(1.0, 380000)})
    # gen_database(16, request)

    contour = create_random_contour(8)
    grid = create_grid(contour, 1.0)

    coord_inner_v = mesh_contour(contour, "out.mesh")
    nb_inner_v = len(coord_inner_v)//2
    scores = calculate_score_array(grid, coord_inner_v)

    out_vertices = compute_vertices(1.0, contour, grid, scores, nb_inner_v)

    # Show inner grid :
    if 1:
        plt.scatter(np.transpose(grid)[0], np.transpose(
            grid)[1], c=scores)  # score map of the grid
        plt.colorbar()
        plt.scatter(np.transpose(out_vertices)[
                    0], np.transpose(out_vertices)[1], color="red")  # points put after interpolation
        plt.title("Score of each point of the grid and position interpolated")
        plt.show()

    return


if __name__ == "__main__":
    main()
