#!/usr/bin/env python3

import rospy
import numpy as np

from sklearn.linear_model import LinearRegression

import cv2

from message_filters import ApproximateTimeSynchronizer, Subscriber
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge.core import CvBridge, CvBridgeError

class VideoStitcher(object):
    """
    """

    def __init__(self):
        """
        """
        # Image Size
        height = rospy.get_param('~height', 1080)
        width = rospy.get_param('~width', 1920)

        # CB(Chessboard) size
        self.cb_row = rospy.get_param('~cb_row', 5)
        self.cb_col = rospy.get_param('~cb_row', 4)
        self.cb_blank = rospy.get_param('cb_blank', 2)
        
        # ROS-OpenCV Bridge
        self.bridge = CvBridge()

        # Transformation Matrix
        self.saved_homo_matrix = None

        self.fitted_left_corners = np.zeros(shape=((self.cb_row * self.cb_col), 1, 2))

        # Time Sync Subscriber
        left_image_sub = Subscriber('/left_camera/image_raw', Image)
        right_image_sub = Subscriber('/right_camera/image_raw', Image)
        
        time_sync = ApproximateTimeSynchronizer([left_image_sub, right_image_sub], queue_size=10, slop=0.5)
        time_sync.registerCallback(self.callback)

        # Stitched Image Publisher
        self.stitched_image_pub = rospy.Publisher('/stitched_image_raw', Image, queue_size=10)

        # Detected and Predicted Chessboard Corners
        corners_shape = ((self.cb_row * self.cb_col), 1, 2)
        self.left_corners = np.zeros(shape=(corners_shape))
        self.predicted_left_corners = np.zeros(shape=(corners_shape))
        self.right_corners = np.zeros(shape=(corners_shape))

    def callback(self, left, right):
        try:
            cv_left_image = self.bridge.imgmsg_to_cv2(left, "bgr8")
            cv_right_image = self.bridge.imgmsg_to_cv2(right, "bgr8")

            if self.saved_homo_matrix is None:
                # try:
                left_ret, left_corners = cv2.findChessboardCorners(cv_left_image, (self.cb_row, self.cb_col), None)
                right_ret, right_corners = cv2.findChessboardCorners(cv_right_image, (self.cb_row, self.cb_col), None)

                print(left_ret, right_ret)

                self.left_corners = left_corners
                self.right_corners = right_corners

                corners_x = np.zeros(shape=(self.cb_row, self.cb_col))
                corners_y = np.zeros(shape=(self.cb_row, self.cb_col))

                # Predict a symmetric corners with each one row point from the left corners
                for j in range(self.cb_row):
                    each_row_x_points = []
                    each_row_y_points = []

                    orgin_index = range(self.cb_col)

                    target_index = range(self.cb_blank + self.cb_col, self.cb_blank + (2 * self.cb_col))

                    for i in range(len(left_corners)):
                        if i % self.cb_row == j:
                            each_row_x_points.append(int(left_corners[i][0][0]))
                            each_row_y_points.append(int(left_corners[i][0][1]))

                    fitted_each_row_x_points = self.linearFitter(orgin_index, each_row_x_points, target_index)
                    fitted_each_row_y_points = self.linearFitter(orgin_index, each_row_y_points, target_index)

                    # each_row_x_points = list(reversed(each_row_x_points))
                    # each_row_y_points = list(reversed(each_row_y_points))

                #     # for ii in range(len(fitted_x_points)):
                #         # cv2.circle(cv_left_image, (int(fitted_x_points[ii]), int(fitted_y_points[ii])), 7, (255, 0, 0), -1)

                    # corners_x[j] = np.flip(fitted_each_row_x_points).reshape(1, self.cb_col)
                    # corners_y[j] = np.flip(fitted_each_row_y_points).reshape(1, self.cb_col)
                    
                    corners_x[j] = fitted_each_row_x_points.reshape(1, self.cb_col)
                    corners_y[j] = fitted_each_row_y_points.reshape(1, self.cb_col)


                corners_x = np.ravel(corners_x, order='F').reshape(-1, 1)
                corners_y = np.ravel(corners_y, order='F').reshape(-1, 1)

                self.fitted_left_corners[:, :, 0] = corners_x
                self.fitted_left_corners[:, :, 1] = corners_y

                # self.fitted_left_corners = np.flip(self.fitted_left_corners)

                homography, _ = cv2.findHomography(right_corners, self.fitted_left_corners)
                self.saved_homo_matrix = homography

            output_shape = (cv_left_image.shape[1] + cv_right_image.shape[1], cv_left_image.shape[0])
            result = cv2.warpPerspective(cv_right_image, self.saved_homo_matrix, (output_shape))
            result[0:cv_left_image.shape[0], 0:cv_left_image.shape[1]] = cv_left_image
                        
            self.stitched_image_pub.publish(self.bridge.cv2_to_imgmsg(result, "bgr8"))

            # except:
            # print("Fusck")

        except CvBridgeError as e:
            print(e)
        
    def linearFitter(self, train_x, train_y, target_x):
        """
        """
        fitter = LinearRegression()

        train_x = np.array(train_x).reshape(-1, 1)
        train_y = np.array(train_y).reshape(-1, 1)
        target_x = np.array(target_x).reshape(-1, 1)

        fitter.fit(train_x, train_y)

        return fitter.predict(target_x)

if __name__ == '__main__':
    print("main")
    rospy.init_node('video_stitcher', anonymous=False)
    video_stitcher = VideoStitcher()
    rospy.spin()