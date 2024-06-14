import logging
import boto3
from botocore.exceptions import ClientError
import os
import argparse
import glob
import sys
from subprocess import PIPE, STDOUT, Popen
from pathlib import Path
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if not object_name:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def build_videos(source_directory):
    """Builds video from source_directory. Source directory must be parent folder of ground truth generated using ORA extension.

    :param source_directory: Source directory containing ground truth generated using ORA extension.
    :return: None
    """
    if os.path.isdir(source_directory):
        # Grab all the rgb folders in the source directory
        rgb_folders = glob.glob("{}/*/rgb/".format(source_directory))
        build_process_list = []
        curr_dir = os.getcwd()
        logging.info("Creating videos from images in source_directory - {}. This might take a while based on the length of video to be generated. Logs for video creation are at {}.".format(source_directory, os.path.join(curr_dir, "video_creation_logs")))
        try:
            for folder in rgb_folders:
                # Get parent folder name
                rgb_path = Path(folder)
                camera_folder_name = os.path.basename(rgb_path.parent.absolute())

                # Split till the second occurence of '_' and use the last portion of string. That is, go from World_Cameras_Camera_01 to Camera_01
                camera_folder_name = camera_folder_name.split('_', 2)[-1]

                # Create log folder and log files for video generation
                log_file_path = os.path.join(curr_dir, "video_creation_logs", "{}.log".format(camera_folder_name))
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                log_file = open(log_file_path, "w") 
                
                # Run ffmpeg command for creating videos
                build_process = Popen(
                    "ffmpeg -nostdin -r 30 -f image2 -s 1920x1080 -start_number 0 -y -i {}/%d.jpeg -vcodec libx264 -crf 23 -pix_fmt yuv420p {}/{}.mp4".format(
                        folder, folder, camera_folder_name
                    ),
                    shell=True,stdout=log_file, stderr=log_file
                )
                build_process_list.append(build_process)

            # Wait for all ffmpeg processes to finish
            for process in build_process_list:
                process.wait()
            logging.info("Finished creating videos from images.")
        except Exception as e:
            logging.error("Could not run ffmpeg command due to error - {}. \n Note, this operation requires ffmpeg to be installed".format(e))
    else:
        logging.error("Invalid source_directory passed.")


def get_args():
    parser = argparse.ArgumentParser("SDG Utils")
    parser.add_argument('-sd', '--source_directory', required=False, help='Path to source folder to copy.')
    parser.add_argument('-bu', '--build', required=False, action='store_true', help='Build videos in source foler.')
    parser.add_argument('-f', '--format_to_copy', required=False, help='Format of files to match and upload, can be left empty for a single file.')
    parser.add_argument('-dd', '--destination_directory', required=False, help='Destination folder in S3 folder.')
    parser.add_argument('-sf', '--source_file', required=False, help='Path to source file to copy.')
    parser.add_argument('-df', '--destination_file', required=False, help='Destination file in S3 folder')
    parser.add_argument('-b', '--bucket', required=False, help='S3 bucket to copy data to.')
    args = parser.parse_args()
    return args

def main():
    args = get_args()
    source_directory = args.source_directory
    destination_directory = args.destination_directory
    format_to_copy = args.format_to_copy
    source_file = args.source_file
    destination_file = args.destination_file
    bucket = args.bucket
    build = args.build

    # Build videos from images present in source directory
    if build:
        build_videos(source_directory)

    # If S3 bucket is provided, upload content to S3 bucket.
    if bucket:
        # Upload multiple files matching a specific format from a directory.
        if source_directory:
            if os.path.isdir(source_directory):
                files = glob.glob("{}/**/*.{}".format(source_directory, format_to_copy),recursive=True)
                logging.info("Total files to copy - {}".format(len(files)))
                for file in files:
                    logging.info("Copying file {}".format(file))
                    file_name = os.path.basename(file)
                    destination_object = None
                    if destination_directory:
                        destination_object = destination_directory + "/" + file_name
                    upload_file(file, bucket, destination_object)
            else:
                logging.error("Invalid source_directory passed.")
        # Upload a single file to the s3 bucket.
        if source_file:
            if os.path.isfile(source_file):
                logging.info("Copying file {}".format(source_file))
                upload_file(source_file, bucket, destination_file)
            else:
                logging.error("Invalid source_file passed.")


if __name__ == "__main__":
    main()