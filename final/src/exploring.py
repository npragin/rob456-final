#!/usr/bin/env python3

# This assignment lets you both define a strategy for picking the next point to explore and determine how you
#  want to chop up a full path into way points. You'll need path_planning.py as well (for calculating the paths)
#
# Note that there isn't a "right" answer for either of these. This is (mostly) a light-weight way to check
#  your code for obvious problems before trying it in ROS. It's set up to make it easy to download a map and
#  try some robot starting/ending points
#
# Given to you:
#   Image handling
#   plotting
#   Some structure for keeping/changing waypoints and converting to/from the map to the robot's coordinate space
#
# Slides

# The ever-present numpy
import numpy as np
from scipy.ndimage import convolve

# Your path planning code
import path_planning as path_planning
# Our priority queue
import heapq

# Using imageio to read in the image
import imageio
import rospy


# -------------- Showing start and end and path ---------------
def plot_with_explore_points(im_threshhold, zoom=1.0, robot_loc=None, explore_points=None, best_pt=None):
    """Show the map plus, optionally, the robot location and points marked as ones to explore/use as end-points
    @param im - the image of the SLAM map
    @param im_threshhold - the image of the SLAM map
    @param robot_loc - the location of the robot in pixel coordinates
    @param best_pt - The best explore point (tuple, i,j)
    @param explore_points - the proposed places to explore, as a list"""

    # Putting this in here to avoid messing up ROS
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 2)
    axs[0].imshow(im_threshhold, origin='lower', cmap="gist_gray")
    axs[0].set_title("original image")
    axs[1].imshow(im_threshhold, origin='lower', cmap="gist_gray")
    axs[1].set_title("threshold image")
    """
    # Used to double check that the is_xxx routines work correctly
    for i in range(0, im_threshhold.shape[1]-1, 10):
        for j in range(0, im_threshhold.shape[0]-1, 2):
            if is_reachable(im_thresh, (i, j)):
                axs[1].plot(i, j, '.b')
    """

    # Show original and thresholded image
    if explore_points is not None:
        for p in explore_points:
            axs[1].plot(p[0], p[1], '.b', markersize=2)

    for i in range(0, 2):
        if robot_loc is not None:
            axs[i].plot(robot_loc[0], robot_loc[1], '+r', markersize=10)
        if best_pt is not None:
            axs[i].plot(best_pt[0], best_pt[1], '*y', markersize=10)
        axs[i].axis('equal')

    for i in range(0, 2):
        # Implements a zoom - set zoom to 1.0 if no zoom
        width = im_threshhold.shape[1]
        height = im_threshhold.shape[0]

        axs[i].set_xlim(width / 2 - zoom * width / 2, width / 2 + zoom * width / 2)
        axs[i].set_ylim(height / 2 - zoom * height / 2, height / 2 + zoom * height / 2)


# -------------- For converting to the map and back ---------------
def convert_pix_to_x_y(im_size, pix, size_pix):
    """Convert a pixel location [0..W-1, 0..H-1] to a map location (see slides)
    Note: Checks if pix is valid (in map)
    @param im_size - width, height of image
    @param pix - tuple with i, j in [0..W-1, 0..H-1]
    @param size_pix - size of pixel in meters
    @return x,y """
    if not (0 <= pix[0] <= im_size[1]) or not (0 <= pix[1] <= im_size[0]):
        raise ValueError(f"Pixel {pix} not in image, image size {im_size}")

    return [size_pix * pix[i] / im_size[1-i] for i in range(0, 2)]


def convert_x_y_to_pix(im_size, x_y, size_pix):
    """Convert a map location to a pixel location [0..W-1, 0..H-1] in the image/map
    Note: Checks if x_y is valid (in map)
    @param im_size - width, height of image
    @param x_y - tuple with x,y in meters
    @param size_pix - size of pixel in meters
    @return i, j (integers) """
    pix = [int(x_y[i] * im_size[1-i] / size_pix) for i in range(0, 2)]

    if not (0 <= pix[0] <= im_size[1]) or not (0 <= pix[1] <= im_size[0]):
        raise ValueError(f"Loc {x_y} not in image, image size {im_size}")
    return pix


def is_reachable(im, pix):
    """ Is the pixel reachable, i.e., has a neighbor that is free?
    Used for
    @param im - the image
    @param pix - the pixel i,j"""

    # Returns True (the pixel is adjacent to a pixel that is free)
    #  False otherwise
    # You can use four or eight connected - eight will return more points
    # YOUR CODE HERE
    #print(pix)
    neighbors = path_planning.get_neighbors(im, pix)
    if not neighbors:
        return False
    else:
        return True


def find_all_possible_goals(im):
    """ Find all of the places where you have a pixel that is unseen next to a pixel that is free
    It is probably easier to do this, THEN cull it down to some reasonable places to try
    This is because of noise in the map - there may be some isolated pixels
    @param im - thresholded image
    @return dictionary or list or binary image of possible pixels"""

    # YOUR CODE HERE
    rospy.loginfo("DOING THINGS")
    
    # Define masks for unseen and free pixels
    unseen_mask = (im == 128)  # Replace with the actual value for "unseen" pixels
    free_mask = (im == 255)  # Replace with the actual value for "free" pixels
    
    # Define a convolution kernel to check for adjacent unseen pixels
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]])
    
    #print(f"unseen_mask shape: {unseen_mask.shape}")
    #print(f"kernel shape: {kernel.shape}")
    #print(f"map shape: {map.shape}")
    #print(f"freemask shape: {free_mask.shape}")

    # Identify unseen neighbors by convolving the unseen_mask
    unseen_neighbors = convolve(unseen_mask.astype(int), kernel, mode="constant", cval=0)
    rospy.loginfo("CONVOLVED")
    # Find free pixels that are adjacent to unseen pixels
    valid_points_mask = free_mask & (unseen_neighbors > 0)
    rospy.loginfo("MADE VALID MASK")
    # Get coordinates of valid points
    valid_points = np.argwhere(valid_points_mask)
    rospy.loginfo("MADE VALID POINTS")
    # Swap axes if needed
    valid_points_swapped = [(y, x) for (x, y) in valid_points] #np.column_stack((valid_points[:,1], valid_points[:0]))
    rospy.loginfo("SWAPPEDEM")
    #print(valid_points_swapped)
    
    # Filter points to include only reachable ones
    reachable_points = [point for point in valid_points_swapped if is_reachable(im, point)]
    #mask = is_reachable(im, valid_points_swapped)
    #reachable_points = valid_points_swapped[mask]
    rospy.loginfo("FOUND REACHABLES")
    # Return as set of tuples (row, column format)
    return set(map(tuple, reachable_points))
    

def find_best_point(possible_points, robot_loc):
    """ Pick one of the unseen points to go to
    @param im - thresholded image
    @param possible_points - possible points to chose from
    @param robot_loc - location of the robot (in case you want to factor that in)
    """
    # YOUR CODE HERE
    min_distance = float('inf')
    closest_point = None
    i, j = robot_loc
    for x, y in possible_points:
        distance = np.sqrt((i - x)**2 + (j - y)**2)
        if distance < min_distance:
            min_distance = distance
            closest_point = (x, y)

    return closest_point

def find_furthest_point(possible_points, robot_loc):
    """
    Pick the furthest point to go to.
    
    @param possible_points: possible points to choose from
    @param robot_loc: location of the robot (x, y)
    """
    max_distance = -float('inf')  # Start with the smallest possible value
    furthest_point = None
    i, j = robot_loc

    for x, y in possible_points:
        distance = np.sqrt((i - x)**2 + (j - y)**2)  # Calculate Euclidean distance
        if distance > max_distance:  # Compare with max_distance
            max_distance = distance
            furthest_point = (x, y)

    return furthest_point


def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points."""
    return np.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def calculate_vector(point1, point2):
    """Calculate the vector from point1 to point2."""
    return point2[0] - point1[0], point2[1] - point1[1]

def find_waypoints(im, path):
    """ Place waypoints along the path
    @param im - the thresholded image
    @param path - the initial path
    @ return - a new path"""

    # Again, no right answer here
    # YOUR CODE HERE
    distance_threshold = 5
    waypoints = [path[0]]
    cumulative_distance = 0
    previous_vector = None

    for i in range(1, len(path)):
        # Calculate distance and vector
        distance = calculate_distance(path[i - 1], path[i])
        current_vector = calculate_vector(path[i - 1], path[i])

        # Check for a change in direction
        if previous_vector is not None and current_vector != previous_vector:
            waypoints.append(path[i - 1])
            cumulative_distance = 0  # Reset distance when direction changes

        # Add the point if the distance threshold is exceeded
        cumulative_distance += distance
        if cumulative_distance >= distance_threshold:
            waypoints.append(path[i])
            cumulative_distance = 0  # Reset cumulative distance

        # Update previous vector
        previous_vector = current_vector

    # Add the last point as a waypoint if it's not already included
    if waypoints[-1] != path[-1]:
        waypoints.append(path[-1])

    return waypoints


if __name__ == '__main__':
    # Doing this here because it is a different yaml than JN
    import yaml_1 as yaml

    im, im_thresh = path_planning.open_image("map.pgm")

    robot_start_loc = (1940, 1953)

    all_unseen = find_all_possible_goals(im_thresh)
    best_unseen = find_best_point(im_thresh, all_unseen, robot_loc=robot_start_loc)

    plot_with_explore_points(im_thresh, zoom=0.1, robot_loc=robot_start_loc, explore_points=all_unseen, best_pt=best_unseen)

    path = path_planning.dijkstra(im_thresh, robot_start_loc, best_unseen, 50)
    waypoints = find_waypoints(im_thresh, path)
    path_planning.plot_with_path(im, im_thresh, zoom=0.1, robot_loc=robot_start_loc, goal_loc=best_unseen, path=waypoints)

    # Depending on if your mac, windows, linux, and if interactive is true, you may need to call this to get the plt
    # windows to show
    # plt.show()

    print("Done")