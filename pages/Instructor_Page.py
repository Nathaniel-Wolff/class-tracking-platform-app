"""This is the actual page instructors will use to access their classes,
log pages covered, and actually generate recaps and lesson plans."""
import streamlit as st
import pandas as pd
import json
from jinja2 import Environment
import boto3
from base_classes import Student, AClass, search_Intervals, separate_interval, clean_and_separate_intervals, fix_series_format
from base_classes import upload_json_to_S3, load_json_from_S3, does_group_exist_yet_aws
from datetime import datetime

st.set_page_config(layout="wide")



def rebuild_curriculum(curriculum_data_dir):
    """Function that uses the current curriculum .json to rebuild the curriculum as a plain dictionary
    (Since it doesn't have relevant methods to really associate with it)."""
    with open(curriculum_data_dir, "r") as c:
        curriculum_data_as_a_dict = json.load(c)


    restored_curriculum_dict = {}
    for level, sublevel_dicts in curriculum_data_as_a_dict.items():
        restored_sublevel_dict = {}
        for sublevel, rows in sublevel_dicts.items():
            restored_sublevel_dict[sublevel] = pd.DataFrame(rows)
        restored_curriculum_dict[level] = restored_sublevel_dict

    return restored_curriculum_dict

def rebuild_curriculum_aws(organization_name, client, bucket_name):
    """AWS based function that uses the current curriculum .json to rebuild the curriculum as a plain dictionary
    (Since it doesn't have relevant methods to really associate with it)."""
    all_paths_key = f"{organization_name}/data/" + "all_paths.json"
    all_paths_object = client.get_object(Bucket=bucket_name, Key=all_paths_key)
    all_paths = json.loads(all_paths_object["Body"].read().decode("utf-8"))

    curriculum_data_as_a_dict, curriculum_data_etag = load_json_from_S3(client, bucket_name, all_paths["Curriculum Data"])

    restored_curriculum_dict = {}
    for level, sublevel_dicts in curriculum_data_as_a_dict.items():
        restored_sublevel_dict = {}
        for sublevel, rows in sublevel_dicts.items():
            restored_sublevel_dict[sublevel] = pd.DataFrame(rows)
        restored_curriculum_dict[level] = restored_sublevel_dict

    return restored_curriculum_dict

def rebuild_student_data_aws(organization_name, client, bucket_name):
    """AWS based function that uses the current student data .json to rebuild the student data as a plain dictionary."""
    all_paths_key = f"{organization_name}/data/" + "all_paths.json"
    all_paths_object = client.get_object(Bucket=bucket_name, Key=all_paths_key)
    all_paths = json.loads(all_paths_object["Body"].read().decode("utf-8"))

    student_data_as_a_dict, curriculum_data_etag = load_json_from_S3(client, bucket_name, all_paths["Students"])
    restored_students_dict = {}
    for student_name, student_dict in student_data_as_a_dict.items():
        repacked_student_object = Student.repack_student(student_dict)

        restored_students_dict[student_name] = repacked_student_object
    return restored_students_dict, curriculum_data_etag, all_paths["Students"]

def rebuild_everything(which_instructor, class_data_dir, instructor_data_dir, template_dir):
    """Function that uses the current .json to rebuild all the AClass and Instructor Objects from respective jsons."""
    with open(class_data_dir, 'r') as f:
        class_data_as_a_dict = json.load(f)
    with open(instructor_data_dir,'r') as g:
        instructor_data_as_a_dict= json.load(g)
    with open(template_dir, 'r') as h:
        template_data_as_a_dict = json.load(h)

    list_of_instructor_names = list(instructor_data_as_a_dict.keys())
    #actually allowing instructors to pick their student objects
    st.markdown("### Choose your name:")
    which_instructor = st.radio("",  # Label displayed above the radio buttons
         options= list_of_instructor_names,
         index=0,  # Optional: Default selected option (index of the list)
         horizontal=False,
         help="Select one from the list.")

    st.markdown(
        """
        <style>
        /* Flex-wrap for horizontal radio options */
        div[data-baseweb="radio"] > div {
            flex-wrap: wrap !important;
            row-gap: 6px;        /* vertical spacing between rows */
            column-gap: 12px;    /* horizontal spacing between buttons */
        }

        /* Allow long labels to wrap nicely */
        div[data-baseweb="radio"] label {
            white-space: normal !important;
            line-height: 1.4em;
            padding-right: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    theirs = instructor_data_as_a_dict[which_instructor]
    class_dicts = theirs #Leaving it in the list for easy rebuilding of the objects
    class_options = list(theirs.keys())
    st.markdown("### Which class would you like to use:")
    class_selected = st.radio("", options = class_options, horizontal=True)

    #retrieving the actual class object, (but as a dict first) selected
    selected_class_dict = class_dicts[class_selected]
    repacked_selected_class = AClass.repack_class_object(class_selected, selected_class_dict)

    return repacked_selected_class, template_data_as_a_dict

def rebuild_everything_aws(organization_name, client, bucket_name):
    """Function that uses the current .jsons to rebuild all the AClass and Instructor Objects from respective jsons.
    This version uses the data in Amazon S3 to do so."""
    all_paths_key = f"{organization_name}/data/" +  "all_paths.json"
    all_paths_object = client.get_object(Bucket = bucket_name, Key = all_paths_key)
    all_paths = json.loads(all_paths_object["Body"].read().decode("utf-8"))



    class_data_as_a_dict, class_data_etag = load_json_from_S3(client, bucket_name, all_paths["Class Data"])
    instructor_data_as_a_dict, instructor_data_etag = load_json_from_S3(client, bucket_name, all_paths["Instructor/Tracker Data"])
    template_data_as_a_dict, template_data_etag = load_json_from_S3(client, bucket_name, all_paths["Template"])


    list_of_instructor_names = list(instructor_data_as_a_dict.keys())
    # actually allowing instructors to pick their student objects
    st.markdown("### Choose the name of the instructor you are:")
    which_instructor = st.radio("",  # Label displayed above the radio buttons
                                options=list_of_instructor_names,
                                index=0,  # Optional: Default selected option (index of the list)
                                horizontal=True,  # Optional: Set to True for horizontal alignment
                                help="Select one from the list.",
                                key = "Unused")

    theirs = instructor_data_as_a_dict[which_instructor]
    class_dicts = theirs  # Leaving it in the list for easy rebuilding of the objects
    class_options = list(theirs.keys())

    class_selected = st.radio("Which class would you like to use", options=class_options, horizontal=True)

    # retrieving the actual class object, (but as a dict first) selected
    selected_class_dict = class_dicts[class_selected]
    repacked_selected_class = AClass.repack_class_object(class_selected, selected_class_dict)

    return repacked_selected_class, template_data_as_a_dict


def choose_instructor(organization_name, client, bucket_name):
    all_paths_key = f"{organization_name}/data/" + "all_paths.json"
    all_paths_object = client.get_object(Bucket=bucket_name, Key=all_paths_key)
    all_paths = json.loads(all_paths_object["Body"].read().decode("utf-8"))

    instructor_data_as_a_dict, instructor_data_etag = load_json_from_S3(client, bucket_name, all_paths["Instructor/Tracker Data"])

    instructor_options = list(instructor_data_as_a_dict.keys())

    st.markdown("### Choose the name of the instructor you are:")
    which_instructor = st.radio("",
                                options=instructor_options,
                                index=0,
                                horizontal=True,
                                help="Select one from the list.")

    return which_instructor, instructor_data_as_a_dict, instructor_data_etag, all_paths

def view_students(all_instructor_data, which_instructor, all_paths, client, bucket_name):
    """A simple function that just displays an instructor's students to them for a given class. Could be used
    for instructors to learn the names/levels of their students easily."""
    import html as real_html

    the_class = choose_a_class(which_instructor, all_instructor_data)
    all_student_data, student_data_etag = load_json_from_S3(client, bucket_name, all_paths["Students"])
    all_curriculum_data, curr_data_etag = load_json_from_S3(client, bucket_name, all_paths["Curriculum Data"]) #need to look up the proper pages covered before

    student_and_levels = []
    student_dfs = {}
    for a_student in the_class.students:
        their_student_object = Student.repack_student(all_student_data[a_student])
        student_current_history = their_student_object.active_curriculum_history
        last_covered = student_current_history[len(student_current_history)-1]

        student_last_level = last_covered[2]
        joined_student_and_level = (", ").join([a_student, student_last_level])

        student_and_levels.append(joined_student_and_level)
        student_last_start_index, student_last_end_index = last_covered[3][0], last_covered[3][1]
        student_last_curriculum_covered = all_curriculum_data[str(float(student_last_level[0]))][student_last_level][student_last_start_index:student_last_end_index+1] #this needs to be fixed later for compatibility issues

        student_df = pd.DataFrame(student_last_curriculum_covered)
        student_dfs[a_student] = student_df

    title = str(the_class.class_ID)
    items = [", ".join(the_class.students), ", ".join(the_class.levels)]

    st.markdown("#### Displayed below is the material the students covered in their last lesson.")
    for student_and_level, their_dataframe in zip(student_and_levels[:len(student_and_levels)], student_dfs.values()):
        st.markdown("### " + student_and_level)
        st.dataframe(their_dataframe)

def view_student_history(which_instructor, all_instructor_data, all_paths, client, bucket_name):
    st.markdown("## Choose the class the student is in.")

    st.markdown("## What is the student's name?")
    the_student = st.text_input("")

    all_curriculum_data, curr_data_etag = load_json_from_S3(client, bucket_name, all_paths[
        "Curriculum Data"])  # need to look up the proper pages covered before

    student_dfs = {}
    if the_student:
        all_student_data, student_data_etag = load_json_from_S3(client, bucket_name, all_paths["Students"])
        st.write(the_student)
        student_dict = all_student_data[the_student]
        repacked_student = Student.repack_student(student_dict)

        for i, piece in enumerate(repacked_student.active_curriculum_history):
            student_last_level = piece[2]
            date = piece[0]
            student_last_start_index, student_last_end_index = piece[3][0], piece[3][1]
            student_last_curriculum_covered = all_curriculum_data[str(float(student_last_level[0]))][
                                                  student_last_level][
                                              student_last_start_index:student_last_end_index + 1]  # this needs to be fixed later for compatibility issues

            student_df = pd.DataFrame(student_last_curriculum_covered)
            student_dfs[date] = student_df


    for name, df in student_dfs.items():
        st.markdown("## " + name)
        this_frame = st.dataframe(df)


def choose_a_class(instructor_data, which_instructor):
    """Simple function used to choose and rebuild an instructor's class."""
    theirs = instructor_data[which_instructor]
    class_dicts = theirs  # Leaving it in the list for easy rebuilding of the objects

    class_options = list(theirs.keys())

    st.markdown("### Which class would you like to use?")
    class_selected = st.radio("", options=class_options, horizontal=True)
    if class_selected:
        # retrieving the actual class object, (but as a dict first) selected
        selected_class_dict = class_dicts[class_selected]
        the_class = AClass.repack_class_object(class_selected, selected_class_dict)
    else:
        st.info("Waiting for your input.")

    return the_class


def log_lesson_and_generate_recap(which_instructor, instructor_data, rebuilt_curriculum, all_student_data, all_students_key, bucket_name, student_data_etag, client,
                                  all_paths):
    """Function that allows an instructor to log the pages covered by the students in the class they selected.
    It then uses a search function to find the corresponding topics they covered, homework, and reading assignments.
    It finally updates the Student objects with their page history. (still working that part out) """

    the_class = choose_a_class(which_instructor, instructor_data)

    template_data_as_a_dict, template_data_etag = load_json_from_S3(client, bucket_name, all_paths["Template"])

    student_pages_covered_dict = {}

    the_date = str(datetime.now().date())
    headers_map = template_data_as_a_dict["headers_to_sections_map"]
    input_header = template_data_as_a_dict["which_header_instructor_input"]

    prepared_template = template_data_as_a_dict["actual_template_string"]

    env = Environment()
    env.filters["fix_series_format"] = fix_series_format

    actual_template_prepared = env.from_string(prepared_template)

    student_and_rows_dict = {}
    corrected_headers_map = {}


    #enforcing the fact that the keys of the headers map must not have spaces in them
    for unfixed_key, value in headers_map.items():
        corrected_headers_map[unfixed_key.rstrip()] = value

    for i, student in enumerate(the_class.students):
        st.markdown("#### What is this student's level?")
        student_level = st.text_input("", key = i)

        pages_student_covered = "Which pages did {} cover? You must report them in this format: Level or Sublevel: start page - end page"
        st.markdown("#### " + pages_student_covered.format(student))
        actual_response = st.text_input("", key = str(pages_student_covered.format(student)))

        if actual_response:
            student_sublevel = actual_response.split(":")[0]
            student_interval = actual_response.split(":")[1]

            student_pages_covered_dict[student] = student_interval
            fetched_level_dict = rebuilt_curriculum[student_level]
            fetched_sublevel_frame = fetched_level_dict[student_sublevel]
            fetched_sublevel_intervals = fetched_sublevel_frame[input_header].tolist()
            this_separated_interval = separate_interval(student_interval)
            these_cleaned_and_grouped_intervals = clean_and_separate_intervals(fetched_sublevel_intervals)


            actual_feteched_sublevel_frame_indices = search_Intervals(these_cleaned_and_grouped_intervals,this_separated_interval[0],this_separated_interval[1]  )
            all_daily_student_data = (the_date, student_level, student_sublevel,actual_feteched_sublevel_frame_indices)

            actual_rows = fetched_sublevel_frame[actual_feteched_sublevel_frame_indices[0]: actual_feteched_sublevel_frame_indices[1] +1 ]

            #mapping original dict to a dict with keys that are a header's corresponding section from the headers map
            fixed_headers_map = dict(zip(corrected_headers_map.values(), corrected_headers_map.keys()))


            for original_key, rows in actual_rows.to_dict().items():
                if original_key in fixed_headers_map.keys():
                    actual_rows[fixed_headers_map[original_key]] = rows
            student_and_rows_dict[student] = actual_rows

            #editing the student's object and updating  the json
            which_student_object = all_student_data[student]
            which_student_object.active_curriculum_history.append(all_daily_student_data)
            #saving the updated student object to the proper dictionary after unpacking
            all_student_data[student] = which_student_object

    complete = st.checkbox("Click here if you are done logging.")
    if complete:
        rendered_template = actual_template_prepared.render(data = student_and_rows_dict, student_pages_covered = student_pages_covered_dict)
        st.write(rendered_template)
        #updating the all_students json based on the students logged
        deserialized_all_student_data = {}


        for student_name, student in all_student_data.items():
            if student is not None:
                deserialized_all_student_data[student_name] =  student.unpack_student()

        updated_all_students_data  = upload_json_to_S3(data = deserialized_all_student_data, a_key = all_students_key, bucket_name = bucket_name, expected_ETAG = student_data_etag)
        st.write("✅Student data updated!")

def main():
    """
    This function contains the main logic of the instructor page.
    """
    # figuring out whether or not the user is from an tutoring group/organization that has already been logged
    st.title("Welcome to the Instructor Page!")
    this_instructor_client = boto3.client("s3")

    st.markdown("### Type the name of your organization.")
    this_instructor_organization_name = st.text_input(label = "", key = "this_instructor_organization_name")

    if this_instructor_organization_name:

        this_bucket_name = "classandlessontrackingplatform-testing-data"



        if does_group_exist_yet_aws(this_instructor_organization_name, this_bucket_name, this_instructor_client):
            which_instructor, this_tracker_dict, this_tracker_etag, this_all_paths = choose_instructor(this_instructor_organization_name, this_instructor_client, this_bucket_name)

            #aws_rebuilt_class_chosen, aws_template_data_dict = rebuild_everything_aws(this_instructor_organization_name, this_instructor_client, this_bucket_name)
            aws_rebuilt_all_students, aws_fetched_students_etag, this_all_students_key = rebuild_student_data_aws(this_instructor_organization_name, this_instructor_client, this_bucket_name)

            action_options = ["Log A Lesson", "View a Student's History", "View a Class", "Other"]
            st.markdown("## What would you like to do?")
            chosen_option = st.radio("", options=action_options, horizontal = True)

            if chosen_option == "Log A Lesson":
                this_rebuilt_curriculum_aws = rebuild_curriculum_aws(this_instructor_organization_name, this_instructor_client, this_bucket_name)

                this_lesson_logged = log_lesson_and_generate_recap(this_tracker_dict, which_instructor, this_rebuilt_curriculum_aws,
                                                                   aws_rebuilt_all_students, this_all_students_key, this_bucket_name, aws_fetched_students_etag, this_instructor_client, this_all_paths)

            if chosen_option == "View a Class":
                this_viewed_class = view_students(which_instructor, this_tracker_dict, this_all_paths, this_instructor_client, this_bucket_name)


            if chosen_option == "View a Student's History":
                this_viewed_student = view_student_history(which_instructor, this_tracker_dict, this_all_paths, this_instructor_client, this_bucket_name)

if __name__ == "__main__":
    main()
