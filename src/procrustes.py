#!/bin/python3

import numpy as np
import math
import scipy.spatial as sp
import matplotlib.pyplot as plt


# @profile
def reg_unit_polygon_gen(nvert: int) -> np.ndarray:
    """Generates a regular unit polygon of nvert vertices

        :param int nvert: The number of vertices

        :return: Vector of coordinates for the nvert vertices
        :rtype: np.ndarray
    """
    coord = np.zeros((nvert, 2))

    theta = np.array(range(nvert)) * 2. * np.pi / nvert
    coord[:, 0] = np.cos(theta)
    coord[:, 1] = np.sin(theta)

    return coord


# @profile
def procrustes(coord: np.ndarray) -> None:
    """Determines a linear transformation of the points of the generated polygon 
    to best conform them to the points of the regular unit polygon

        :param np.ndarray coord: The coordinates of the polygon to transform

        :return: Changes the coordinates of the polygon
        :rtype:
        """

    nvert = len(coord)
    reg_coord = reg_unit_polygon_gen(nvert)

    # plt.plot(coord[:, 0], coord[:, 1])
    # plt.plot(reg_coord[:, 0], reg_coord[:, 1])
    # plt.show()

    # In the procrustes algorithm, points are scaled with the absolute 2-norm,
    # but maybe it is better to scale with the 2-norm scaled by the number of points ???
    reg_coord, coord, disparity = sp.procrustes(reg_coord, coord)

    # plt.plot(coord[:, 0], coord[:, 1])
    # plt.plot(reg_coord[:, 0], reg_coord[:, 1])
    # plt.show()
    return


def main():

    return


if __name__ == "__main__":
    main()
