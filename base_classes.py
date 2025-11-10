
import json
import re
import numpy as np
import boto3
import streamlit as st
from botocore.exceptions import ClientError
import pandas as pd
from collections import defaultdict

st.set_page_config(layout="wide")
st.markdown("""
<style>
/* Enlarge labels for all main input types */
div[data-baseweb="input"] > div > div:first-child,
div[data-baseweb="textarea"] > div > div:first-child,
div[data-baseweb="numberinput"] > div > div:first-child,
div[data-baseweb="select"] > div:first-child,
div[data-baseweb="slider"] > div:first-child,
div[data-baseweb="radio"] > div:first-child {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #111 !important;
}
</style>
""", unsafe_allow_html=True)

#taken from chatgpt
def group_dict_to_dataframes_by_index(data, group_index, retained_headers):
    """
    Groups entries in a dictionary based on the nth element of each value (list or tuple),
    and returns a dictionary of DataFrames (one per group).

    Parameters
    ----------
    data : dict
        Dictionary where values are list-like records.
    group_index : int
        The index of the element in each record to group by.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary mapping group name -> DataFrame of that group.
    """
    grouped = defaultdict(list)


    #grouping entries

    for name, record in data.items():
        group_value = record[group_index]
        grouped[group_value].append(list(record))
    #converting to dataframes
    group_dfs = {}
    for group, records in grouped.items():
        df = pd.DataFrame(records, columns = retained_headers)
        group_dfs[group] = df

    return group_dfs

def does_group_exist_yet_aws(organization_name: str, bucket_name, client):
    """Function that checks if initialization of a new user group is neccesary (web version).
    It checks if the organization has a prefix already in a given bucket."""
    organization_responce = client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=f"{organization_name}/",
        MaxKeys=1
    )
    return "Contents" in organization_responce #should evaluate to Boolean, same as the other function

def valid_number(something):
    """Function used to test if a piece of a split interval is an integer. Used in clean and separate intervals below."""
    try:
        int(something)
        return True
    except ValueError:
        return False


def clean_wrong_interval(wrong_interval):
    interval = []

    for subpart in wrong_interval:
        fixed_subpart = ''.join(re.findall(r'\d', subpart))
        interval.append(fixed_subpart)


    int_subparts = [int(fixed) for fixed in interval]
    tuple_fixed_interval = tuple(int_subparts)
    return tuple_fixed_interval


def upload_jinja_text_to_doc(rendered_report, output_path_key):
    pass
    #blank_doc = Document


def upload_json_to_S3(data, a_key, bucket_name, expected_ETAG: str = None):
    """A simple helper function to upload a json file to S3, given an already prepared bucket
    and a premade key for the json.
    To ensure that another user hasn't modified said json in place before this user uploads an updated copy,
    it also checks the Etag of the file to be uploaded, and only uploads it if the ETag is the same as when the
    function call started."""
    s3_client = boto3.client("s3")
    this_new_data = {}
    try:
        kwargs_for_put_object = dict(
            Bucket=bucket_name,
            Key=a_key,
            Body=json.dumps(data, indent=4).encode("utf-8"),
            ContentType="application/json"
        )

        if expected_ETAG:
            kwargs_for_put_object["IfMatch"] = expected_ETAG

        s3_client.put_object(**kwargs_for_put_object)
        return True

    except ClientError as error:
        if error.response["Error"]["Code"] == "PreconditionFailed": #if the ETag is modified
            st.write(f"ETag mismatch for {a_key}. Merging remote changes and retrying...")
            other_instructor_remote_data, other_instructor_etag = load_json_from_S3(bucket_name, a_key) #downloading the other version of the json that the other instructor edited
            data_merged = merge_instructors_jsons(other_instructor_remote_data, data, this_new_data)
            try:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=a_key,
                    Body=json.dumps(data_merged, indent=4).encode("utf-8"),
                    ContentType="application/json",)
                return True

            except ClientError as other_error:
                st.write(f"Upload failed even after merge. Please try again. This is the error: {other_error}")
                return False


        else:
            st.write(f"Error uploading {a_key}: {error}")
            return False

def load_json_from_S3(client, bucket_name, key):
    """Function to download a json from a given bucket. It will also return the ETag, to be used
    to see if there's a version conflict between given jsons (which will be handled with the below function)"""
    try:
        from_s3 = client.get_object(Bucket = bucket_name, Key = key)
        actual_json = from_s3["Body"].read().decode("utf-8")
        the_etag = from_s3["ETag"].strip('"') #remove quotes
        return json.loads(actual_json), the_etag
    except ClientError as error:
        if error.response["Error"]["Code"] == "NoSuchKey":
            st.write("No file found.")
            return {}, None
        else:
            raise #just raises another client error

    return actual_json, the_etag

def merge_instructors_jsons(other_instructors_dict: dict, current_instructors_dict:dict, new_values: dict):
    """In the event of a version conflict between two instructors simultaneously editing jsons,
     this function takes the current instructor's data and merges it with the first instructor's edited
     data, and uses that to build the updated json."""
    merged_dict = {}
    for a_key, a_value in other_instructors_dict.items():
        if isinstance(a_value, dict):
            # recursively checking to see if we have a nested dict that we need to update associated with the key the other instructor updated
            merged_dict[a_key] = merge_instructors_jsons(other_instructors_dict[a_key], current_instructors_dict.get(a_key, {}), new_values.get(a_key, {}))

        else: #once you have recursed far enough into the other instructors' inner dict of the outer nested dict (typically one level down)
            if a_value == current_instructors_dict.get(a_key): #if the value corresponding to the given key is the same in both instructors' dicts
                merged_dict[a_key] = new_values.get(a_key, a_value) #you can overwrite that key with the one that instructor updated
            else: #if the value corresponding to the given key is different in the other instructors' dict (typically means it isn't a student/class corresponding to the user instructor)
                merged_dict[a_key] = other_instructors_dict.get(a_key, a_value) #just use the other instructors' value

    return merged_dict

def separate_interval(interval):
    """A simple function to convert an interval into a tuple. Wrapped by search_database below."""
    original_list = [piece for piece in interval.split("-")]
    if all(np.array([valid_number(item) for item in original_list])):
        int_list = [int(subpart) for subpart in original_list]
        tuple_interval = tuple(int_list)
    else:
        tuple_interval = clean_wrong_interval(original_list)
    return tuple_interval

def clean_and_separate_intervals(Intervals):
    """A function that will take a string containing an interval and clean it into a interval that
    is split by separate_interval above. Uses a regular expression to match interval format (number 1 - number 2).
    """
    cleaned_and_grouped_intervals = []
    interval_pattern = re.compile(r"^\(?\d+-\d+,?\)?$") #added potential parentheses


    for raw_interval in Intervals:
        all_intervals_one_index = []
        split_interval = raw_interval.split()

        for raw_piece in split_interval:
            if interval_pattern.match(raw_piece):

                intermediate_interval = [piece for piece in raw_piece.rstrip(",").split("-")]
                final_interval = clean_wrong_interval(intermediate_interval)
                all_intervals_one_index.append(final_interval)
        cleaned_and_grouped_intervals.append(all_intervals_one_index)

    return cleaned_and_grouped_intervals

def search_Intervals(Intervals, Start, End):
    """A naive search algorithm that finds the interval
    that finds the index of the interval containing a start index as well as that
    containing the end index, given a specific set of intervals."""

    indices = []
    for intervals in Intervals:
        for interval in intervals: #this is to handle grouped indices
            int_start, int_end = interval[0], interval[1]
            if Start >= int_start and Start <= int_end:
                StartIndex = Intervals.index(intervals)
                indices.append(StartIndex)
            if End >= int_start and End <= int_end:
                EndIndex = Intervals.index(intervals)
                indices.append(EndIndex)

    return indices

def fix_series_format(value):
    if isinstance(value, pd.Series):
        return ", ".join(map(str, value.dropna().tolist()))
    else:
        return str(value)

class Student:
    #LATER: active_curriculum_history needs to be refactored into instructor history
    def __init__(self, student_name, level = None, assessment_history = None, active_curriculum_history = None):
        self.student_name = student_name
        self.level = level if level is not None else []
        self.assessment_history = assessment_history if assessment_history is not None else []
        self.active_curriculum_history = active_curriculum_history if active_curriculum_history is not None else []

    def unpack_student(self):
        """Deserializes a student object."""
        return {self.student_name: [self.level, self.assessment_history, self.active_curriculum_history]}

    @staticmethod
    def repack_student(deserialized_dict):
        """Function that reserializes a student object from a deserialized dictionary."""

        student_name = list(deserialized_dict.keys())[0]
        if pd.isna(student_name) or (
                isinstance(student_name, str) and student_name.strip().lower() == "nan"):
            return None

        else:
            that_student_data = list(deserialized_dict.values())


            #this is an artifact of a problem with the reformatting that will be fixed on later
            return Student(student_name = student_name, level= that_student_data[0][0], assessment_history=that_student_data[0][1], active_curriculum_history =  that_student_data[0][2])


class AClass:
    def __init__(self, class_ID, instructor, active = True, students = None, levels = None):
        self.class_ID = class_ID
        self.instructor = instructor
        self.active  = active
        self.students = students if students is not None else []
        self.levels = levels if levels is not None else []

    def close_class(self):
        pass

    def build_lesson_recap(self):
        pass


    def unpack_class_object(self):
        """This is used for deserialization of an object to be formed into a json. Does require an instance."""

        return {self.class_ID : {"Instructor": self.instructor, "Active": self.active,
                "Students": self.students, "Levels": self.levels}}

    @staticmethod
    def repack_class_object(class_ID, deserialized_dict):
        """Static method that is best associated with AClass. Rebuilds a given set of class data
        (from a json) into a class object."""

        return AClass(class_ID=class_ID, instructor=deserialized_dict["Instructor"], active = deserialized_dict["Active"], students = deserialized_dict["Students"], levels=deserialized_dict["Levels"])

class AnInstructor:
    def __init__(self, name, their_classes = list):
        self.name = name
        self.their_classes  = their_classes

    def unpack_instructor_object(self):
        """This is used for deserialization of an instructor object to be formed into a json. Does require an instance."""
        all_of_instructors_classes = {}

        for each_class in self.their_classes:
            the_class_ID = list(each_class.unpack_class_object().keys())[0]

            unpacked_class_dict = list(each_class.unpack_class_object().values())[0]
            all_of_instructors_classes[the_class_ID] = unpacked_class_dict

        return all_of_instructors_classes

    @staticmethod
    def repack_instructor_object(data):
        """Static method that is best associated with AClass. Rebuilds a given set of class data
        (from a json) into a class object."""
        return AnInstructor(
            name= data["Instructor"],
            their_classes = data["their_classes"]
        )