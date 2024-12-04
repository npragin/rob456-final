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

# Your path planning code
import path_planning as path_planning
# Our priority queue
import heapq

from helpers import world_to_map, map_to_world


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
   
        # Precompute wall and unseen masks
    #reachable_mask = np.vectorize(lambda x, y: is_reachable(im, (x, y)))(*np.indices(im.shape))
    #wall_mask = np.vectorize(lambda x, y: path_planning.is_wall(im, (x, y)))(*np.indices(im.shape))
    unseen_mask = np.vectorize(lambda x, y: path_planning.is_unseen(im, (x, y)))(*np.indices(im.shape))

    # Combine masks to find valid locations
    #valid_mask = ~wall_mask & unseen_mask# & reachable_mask
    print("Got here")

    # Extract valid indices
    valid_points = []
    for x, y in zip(*np.where(unseen_mask)):
        neighbors = path_planning.get_neighbors(im, (x, y))
        if neighbors != None:
            for x, y in neighbors:
                valid_points.append((x, y))
    print("finished the list")
    return set(valid_points)
    

def find_best_point(im, possible_points, robot_loc):
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

def is_wall(map, map_width, point):
    return map[int(round(point[0])) + map_width * int(round(point[1]))] > 0.5

def new_find_best_point(map, map_data, robot_loc):
    #TODO: Fix early termination so we can find optimal path
    #TODO: Make sure paths aren't too close
    #NOTE: If something is wrong check: 1. Whether you should multiply loc[0] or loc[1] 2. If int(round()) is messing anything up, especially di / map_width
    map_width = map_data.width
    priority_queue = []
    robot_map_loc = world_to_map(robot_loc[0], robot_loc[1], map_data)
    heapq.heappush(priority_queue, (0, robot_map_loc)) # use helper and store index
    visited = {}
    parents = {}
    parents[robot_map_loc] = None
    nearest = None
    nearest_distance = np.inf

    while priority_queue and nearest is None:
        curr_node_distance, curr_node = heapq.heappop(priority_queue)

        if curr_node in visited:
            continue

        visited[curr_node] = curr_node_distance

        for di in [-map_width, 0, map_width]:
            for dj in [-1, 0, 1]:
                if di == 0 and dj == 0:
                    continue

                neighbor = curr_node + di + dj # Just add di and dj to curr_node which is now an int
                neighbor_distance = curr_node_distance + np.linalg.norm((di / map_width, dj))

                if map[neighbor] >= 50 or neighbor >= map_width * map_data.height: # Can replace this with just map[neighbor] > 0.5
                    continue
                
                if neighbor not in visited:
                    parents[neighbor] = curr_node
                    heapq.heappush(priority_queue, (neighbor_distance, neighbor))

                if map[neighbor] == -1 and neighbor_distance < nearest_distance: # Can just use neighor which is now an int
                    nearest = neighbor
                    nearest_distance = neighbor_distance
                    break
            
            if nearest:
                break

    path = []
    current = nearest
    count = 0
    while current:
        if count % 10 == 0:
            path.append(map_to_world(current, map_data))
        current = parents[current]
        
    path.reverse()

    return [path[-1]]

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
    distance_threshold = 50
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

    path = path_planning.dijkstra(im_thresh, robot_start_loc, best_unseen)
    waypoints = find_waypoints(im_thresh, path)
    path_planning.plot_with_path(im, im_thresh, zoom=0.1, robot_loc=robot_start_loc, goal_loc=best_unseen, path=waypoints)

    # Depending on if your mac, windows, linux, and if interactive is true, you may need to call this to get the plt
    # windows to show
    # plt.show()

    print("Done")
