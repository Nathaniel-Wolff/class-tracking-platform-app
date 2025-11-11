import streamlit as st
import pandas as pd
import os
import numpy as np
import json
from jinja2 import Environment
from base_classes import Student, AnInstructor, AClass, fix_series_format, load_json_from_S3, group_dict_to_dataframes_by_index
import boto3
from botocore.exceptions import ClientError
from itertools import groupby

#This page is the page for either the initialization of a new user group (ie, a tutoring company, school, individual tutor, etc)
"""This function executes all the functions used to initialize the data for a new organization.
   It requires a bucket to have already been made by the AWS S3 Administrator. It is provided by the user as text input."""
#or the redirection of a user to authenticate their role as an admin to update classes or to find their page if they're an instructor.

st.set_page_config(layout="wide")


@st.cache_data
# def does_group_exist_yet(organization_name: str):
#     """Function that checks if initialization of a new user group is neccesary. It checks if the student tracker files exists."""
#     what_should_be_path = os.getcwd()
#     does_it = os.path.exists(os.path.join(what_should_be_path + "/" + organization_name))
#     return does_it

def does_group_exist_yet_aws(_organization_name: str, _bucket_name, _client):
    """Function that checks if initialization of a new user group is neccesary (web version).
    It checks if the organization has a prefix already in a given bucket."""
    organization_responce = _client.list_objects_v2(
        Bucket=_bucket_name,
        Prefix=f"{_organization_name}/",
        MaxKeys=1
    )
    return "Contents" in organization_responce #should evaluate to Boolean, same as the other function

# def build_new_group_directories(organization_name: str, which_term):
#     """This function aids in initialization of a new group by building directories
#     corresponding to a tracker of current students, current instructors, current classes, and curriculum.
#     """
#
#     base_directory = os.path.join(organization_name, "data", )
#     #making a directory for all of the parsed files from the organization
#     parsed_files_name = os.path.join(base_directory, "parsed-files")
#     os.makedirs(parsed_files_name, exist_ok=True)
#     #making a directory for all of the unparsed (raw) files for later viewing
#     raw_files_name = os.path.join(base_directory, "raw-files")
#     os.makedirs(raw_files_name, exist_ok=True)
#     #making directory for a master student tracker (in a csv format)
#     students_tracker = os.path.join(base_directory, "master-students-tracker")
#     os.makedirs(students_tracker, exist_ok=True)
#     #making a directory for a current classes tracker (in the future, there will be a way to track student data over time, like their class history
#     class_tracker= os.path.join(base_directory, which_term + " Classes")
#     os.makedirs(class_tracker, exist_ok = True)
#
#     #making directory for a master instructor tracker (in a csv format)
#     instructors_tracker = os.path.join(base_directory, "master-instructors-tracker")
#     os.makedirs(instructors_tracker, exist_ok=True)
#     #making a directory for the curriculum data
#     curriculum_tracker = os.path.join(base_directory, "curriculum")
#     os.makedirs(curriculum_tracker, exist_ok=True)
#
#     #making a directory for the template
#     template = os.path.join(base_directory,"recap-template")
#     os.makedirs(template, exist_ok=True)
#
#     return base_directory, parsed_files_name, raw_files_name, students_tracker, instructors_tracker, curriculum_tracker, class_tracker, template

def build_new_group_subprefixes_online(organization_name: str, bucket, client):
    """Function that 'builds' subprefixes for a given organization that has just made a prefix """
    base_directory = os.path.join(organization_name, "data", )
    # making a directory for all of the parsed files from the organization
    parsed_files_name = os.path.join(base_directory, "parsed-files")
    os.makedirs(parsed_files_name, exist_ok=True)
    # making a directory for all of the unparsed (raw) files for later viewing
    raw_files_name = os.path.join(base_directory, "raw-files")
    os.makedirs(raw_files_name, exist_ok=True)
    # making directory for a master student tracker (in a csv format)
    students_tracker = os.path.join(base_directory, "master-students-tracker")
    os.makedirs(students_tracker, exist_ok=True)
    # making a directory for a current classes tracker (in the future, there will be a way to track student data over time, like their class history
    which_term = st.text_input("Write the name of the term that the current classes are in.")
    class_tracker = os.path.join(base_directory, which_term + " Classes")
    os.makedirs(class_tracker, exist_ok=True)

    # making directory for a master instructor tracker (in a csv format)
    instructors_tracker = os.path.join(base_directory, "master-instructors-tracker")
    os.makedirs(instructors_tracker, exist_ok=True)
    # making a directory for the curriculum data
    curriculum_tracker = os.path.join(base_directory, "curriculum")
    os.makedirs(curriculum_tracker, exist_ok=True)

    # making a directory for the template
    template = os.path.join(base_directory, "recap-template")
    os.makedirs(template, exist_ok=True)

    return base_directory, parsed_files_name, raw_files_name, students_tracker, instructors_tracker, curriculum_tracker, class_tracker, template

def build_student_trackers_and_instructors(new_data):
    """This function actually builds csv student/instructor trackers during
     intialization and initializes a json containing class histories for each student."""

    all_students = {}  # dictionary containing all student "profiles" (objects) with their names as the key

    st.markdown("#### You must now provide, in a case-sensitive manner, the header of the column you use to demarcate separate classes.")
    column_to_split = st.text_input("", key = "column_to_split")

    st.markdown("#### You must now provide, in a case-sensitive manner, the header of the column you use to demarcate students' names.")
    student_name_column = st.text_input("", key = "student_name_column")

    st.markdown(
        "#### You must now provide, in a case-sensitive manner, the header of the column you use to demarcate instructors' names.")
    instructor_name_column = st.text_input(
        "", key = "instructor_name_column")

    st.markdown("#### You must now provide, in a case-sensitive manner, the header of the column you use to demarcate "
        "the actual names of a specific class. ")
    class_IDs = st.text_input("", key = "class_IDs")

    st.markdown("#### You must now provide, in a case-sensitive manner, the header of the column you use to demarcate the students' levels.")
    level_IDs = st.text_input("", key  = "text_input")

    if all([column_to_split, student_name_column, instructor_name_column, class_IDs, level_IDs]):
        student_names  = new_data[student_name_column].unique()
        instructor_names = new_data[instructor_name_column].unique()

        #Here, we initialize a list of student and instructor objects for later use in lesson recap and semester report generation
        student_names_as_list = new_data[student_name_column].tolist()
        frame_level_IDs = new_data[level_IDs].tolist()
        st.write(frame_level_IDs)

        for student_name in student_names:
            student_name_index  = student_names_as_list.index(student_name)
            st.write(student_name_index)
            student_initial_level = frame_level_IDs[student_name_index]
            this_student = Student(student_name = student_name, level = student_initial_level)
            all_students[student_name] = this_student

        #building instructor objects up front, associating them with their name in a dictionary
        all_instructors_classes = {}
        for instructor_name in instructor_names:
            if type(instructor_name) is not float: #this worked for this version but needs to be not 'harcoded' ish later
                this_instructor_object = AnInstructor(name = instructor_name, their_classes=[])
                all_instructors_classes[instructor_name] = this_instructor_object

        #"""Now we split the raw dataframe into different dataframes for each class. """
        column_to_split_series = new_data[str(column_to_split)]

        all_broken_indices = column_to_split_series[column_to_split_series.isna()].index.tolist() #where None is achieved in the column marking different classes
        all_classes_dict = {}

        last = 0
        for stop in all_broken_indices:
            individual_class_frame = new_data[last+1:stop]

            #inner check to remove null dataframes from extra lines
            if not individual_class_frame[str(column_to_split)].empty:
                #building all aClass objects in one pass, using AClass class
                this_teacher_name = individual_class_frame[instructor_name_column].iloc[0] #this works now but other formats could break this line
                these_students = individual_class_frame[student_name_column].tolist()
                this_ID = individual_class_frame[class_IDs].iloc[0] #this works now but other formats might break this line
                this_class_object = AClass(class_ID = this_ID, instructor = this_teacher_name, active = True, students = these_students)
                all_classes_dict[this_ID] = this_class_object

                #updating all instructor objects with their respective classes
                #fixed to deal with nan values
                if not pd.isna(this_teacher_name):
                    all_instructors_classes[this_teacher_name].their_classes.append(this_class_object)

            last = stop
        return all_classes_dict, all_instructors_classes, all_students
    else:
        st.info("You must enter a value into all of the fields to proceed.")

def build_curriculum_tracker(curriculum_page):
    """
        Processes the curriculum spreadsheet and prepares it to be dumped into JSON later.
        Handles multi-level splitting, optionally splitting further by chapter/module.
        """

    # --- Initialize session state for this flow ---
    if "curriculum_step" not in st.session_state:
        st.session_state["curriculum_step"] = "choose_level_header"
    if "individual_level_frames" not in st.session_state:
        st.session_state["individual_level_frames"] = None
    if "chosen_level_splitting_column" not in st.session_state:
        st.session_state["chosen_level_splitting_column"] = None
    if "chosen_further_splitting_column" not in st.session_state:
        st.session_state["chosen_further_splitting_column"] = None
    if "deserialized_curriculum" not in st.session_state:
        st.session_state["deserialized_curriculum"] = None

    # -------------------------------
    # Step 1: Choose main splitting column
    if st.session_state["curriculum_step"] == "choose_level_header":
        st.markdown("## Choose the header that demarcates different levels.")
        level_splitting_column = st.radio(
            "", options=curriculum_page.columns.values,
            key="level_splitting_column", horizontal=True
        )
        if st.button("Continue", key="first_continue"):
            # Split the dataframe into levels based on NaN boundaries
            column_to_split_series = curriculum_page[level_splitting_column]
            all_broken_indices = column_to_split_series[column_to_split_series.isna()].index.tolist()
            individual_level_frames = [curriculum_page[last + 1:stop] for last, stop in
                                       zip([-1] + all_broken_indices[:-1], all_broken_indices)]

            st.session_state["individual_level_frames"] = individual_level_frames
            st.session_state["chosen_level_splitting_column"] = level_splitting_column
            st.session_state["curriculum_step"] = "ask_further_split"
            return

    # -------------------------------
    # Step 2: Ask if further splitting
    elif st.session_state["curriculum_step"] == "ask_further_split":
        st.markdown("#### Do you need to split levels further (by chapter/module)?")
        do_we_split_further = st.radio("", ["No", "Yes"], key="split_further", horizontal=True)
        if st.button("Continue", key="split_further_continue"):
            if do_we_split_further == "Yes":
                st.session_state["curriculum_step"] = "choose_further_column"
            else:
                st.session_state["curriculum_step"] = "done_no_further_split"
            return

    # -------------------------------
    # Step 3: Choose column for further splitting
    elif st.session_state["curriculum_step"] == "choose_further_column":
        st.markdown("#### Choose the column used for further splitting.")
        further_splitting_column = st.radio(
            "", options=curriculum_page.columns.values,
            key="further_splitting_column", horizontal=True
        )
        if st.button("Continue", key="other_continue"):
            st.session_state["chosen_further_splitting_column"] = further_splitting_column
            st.session_state["curriculum_step"] = "split_further_done"
            return

    # -------------------------------
    # Step 4: Process further split
    elif st.session_state["curriculum_step"] == "split_further_done":
        levels_and_material_dict = {}
        chosen_col = st.session_state["chosen_further_splitting_column"]
        individual_level_frames = st.session_state["individual_level_frames"]
        level_splitting_column = st.session_state["chosen_level_splitting_column"]

        for individual_level_frame in individual_level_frames:
            st.write("Current frame shape:", individual_level_frame.shape)


            if not individual_level_frame.empty:
                base_level = individual_level_frame[level_splitting_column].iloc[0]
                change_points = individual_level_frame[chosen_col] != individual_level_frame[chosen_col].shift()
                change_indices = np.where(change_points)[0]  #positions, not labels (had to be fixed)
                individual_frame_dict = {}


                for i, start in enumerate(change_indices):
                    end = change_indices[i + 1] if i + 1 < len(change_indices) else len(individual_level_frame)
                    sublevel = individual_level_frame[chosen_col].iloc[start]

                    individual_frame_dict[sublevel] = individual_level_frame.iloc[start:end]

                levels_and_material_dict[base_level] = individual_frame_dict

        deserialized_curriculum = deserialize_curriculum_data(levels_and_material_dict)
        if deserialized_curriculum:
            st.session_state["deserialized_curriculum"] = deserialized_curriculum
            st.session_state["curriculum_step"] = "done"
            st.write("Curriculum processing complete.")
            return deserialized_curriculum
        else:
            st.info("Something went wrong. Please try again.")

    # -------------------------------
    # Step 5: No further split needed
    elif st.session_state["curriculum_step"] == "done_no_further_split":
        levels_and_material_dict = {}
        individual_level_frames = st.session_state["individual_level_frames"]
        level_splitting_column = st.session_state["chosen_level_splitting_column"]

        for frame in individual_level_frames:
            if not frame.empty:
                base = frame[level_splitting_column].iloc[0]
                levels_and_material_dict[base] = {base: frame}

        deserialized_curriculum = deserialize_curriculum_data(levels_and_material_dict)
        st.session_state["deserialized_curriculum"] = deserialized_curriculum
        st.session_state["curriculum_step"] = "done"
        st.write("Curriculum processing complete.")
        return deserialized_curriculum

def semester_data_initialization(organization_name: str, bucket_name: str, client, correct_password):
    """This function executes all the functions used to initialize the data for a new organization.
    It requires a bucket to have already been made by the AWS S3 Administrator. It is provided by the user as text input."""

    st.sidebar.title("Access")
    st.markdown("### Enter your organization's password in the field on the top left to proceed to initialization.")
    admin_password = st.sidebar.text_input("", type="password")

    if admin_password == correct_password:
        st.markdown("## Administrator Validated: Please Input the Class Data for the Semester.")

        st.markdown("## Please upload your master organization data file. It must be either a spreadsheet in an .xlsx format.")
        spreadsheet = st.file_uploader("", type=["csv", "xlsx"])



        if spreadsheet:
            st.write("success!")

            if spreadsheet.name.endswith(".csv"):
                df = pd.read_csv(spreadsheet)
                st.write(df)
            elif spreadsheet.name.endswith(".xlsx"):
                xls = pd.ExcelFile(spreadsheet)

                st.markdown(
                    "## You must now choose a page from that sheet that corresponds to this semester:")
                which_semester = st.selectbox("", options = xls.sheet_names)
                if which_semester:
                    if which_semester in xls.sheet_names:
                        st.success(f"Loaded sheet: {which_semester}")
                        st.markdown(
                            "## You must now say on which row (starting from 0) the header (row with titles of the columns) of your spreadsheet is. Given that, the spreadsheet will be displayed below. If it looks good, continue.")
                        header_index = st.text_input("", key = 2)
                        st.write(pd.read_excel(spreadsheet))
                        if header_index:
                            this_semester_page = pd.read_excel(spreadsheet, sheet_name = which_semester, header = int(header_index))
                            st.write(this_semester_page)
                            # building directories
                            st.markdown(
                                "## Write the name of the term that the current classes are in.")
                            which_term = st.text_input("")

                            # actually making the trackers

                            built_trackers = build_student_trackers_and_instructors(
                                this_semester_page)

                            if built_trackers:
                                all_classes, trackers, all_students = built_trackers

                                all_deserialized_classes = {}
                                all_deserialized_trackers = {}
                                all_deserialized_students = {}

                                for class_ID, its_data in all_classes.items():
                                    deserialized_class = its_data.unpack_class_object()
                                    all_deserialized_classes[class_ID] = deserialized_class

                                for student_ID, students_data in all_students.items():
                                    deserialized_student = students_data.unpack_student()
                                    all_deserialized_students[student_ID] = deserialized_student

                                for instructor_name, their_data in trackers.items():
                                    deserialized_tracker = their_data.unpack_instructor_object()
                                    all_deserialized_trackers[instructor_name] = deserialized_tracker


                                st.markdown(
                                    "## Please upload your lesson content master. It must be either a spreadsheet in a .csv or .xlsx format.")
                                lesson_content = st.file_uploader(
                                    "",
                                    type=["csv", "xlsx"], key = "other input")

                                if lesson_content:
                                    lesson_content_name = lesson_content.name
                                    st.markdown("## Success!")
                                    if lesson_content_name.endswith(".csv"):
                                        df = pd.read_csv(lesson_content)

                                    elif lesson_content_name.endswith(".xlsx"):
                                        content_xls = pd.ExcelFile(lesson_content)
                                        st.markdown(
                                            "## You must now choose a page from that sheet that corresponds to the curriculum you want to use:")
                                        which_curriculum = st.selectbox(
                                            "",
                                            options=content_xls.sheet_names)
                                        if which_curriculum:
                                            if which_curriculum in content_xls.sheet_names:
                                                st.success(f"Loaded sheet: {which_curriculum}")
                                                st.markdown(
                                                    "## You must now say on which row (starting from 0) the header (row with titles of the columns) of the curiculum spreadsheet is. Given that, the spreadsheet will be displayed below. If it looks good, keep going.")

                                                cur_header_index = st.text_input(
                                                    "", key = "other one again")
                                                if cur_header_index:
                                                    this_curriculum_page = pd.read_excel(content_xls,
                                                                                         sheet_name=which_curriculum,
                                                                                         header=int(cur_header_index))
                                                    # fixed the below line to remove None or Nan column headers (really separators)
                                                    these_curriculum_headers = [
                                                        col for col in this_curriculum_page.columns
                                                        if pd.notna(col) and not str(col).startswith("Unnamed")
                                                    ]
                                                    st.write(this_curriculum_page)

                                                    all_deserialized_curriculum = build_curriculum_tracker(this_curriculum_page)



                                                    this_template_configured = initialize_and_configure_template(these_curriculum_headers)
                                                    if this_template_configured:
                                                        this_template_dict = this_template_configured[4]
                                                        this_filename_dict = get_filenames_from_user()
                                                        if this_filename_dict:

                                                            # unused now, could be used if the app is run in local mode
                                                            # this_class_data, this_instructor_data, this_curriculum_data, this_template_data = dump_semester_data(all_deserialized_classes, all_deserialized_trackers,
                                                            # all_deserialized_students, all_deserialized_curriculum, this_template_dict, directories, this_filename_dict)
                                                            this_class_key, this_instructor_key, this_curriculum_key, this_template_key = dump_semester_data_aws(
                                                                all_deserialized_classes, all_deserialized_trackers,
                                                                all_deserialized_students, all_deserialized_curriculum, this_template_dict,
                                                                organization_name, which_term, bucket_name, client, this_filename_dict)
                                                            return this_class_key, this_instructor_key, this_curriculum_key, this_template_key
                                                            st.markdown("## Data successfully initialized. check the directory for details.")
                    #else:
                        #st.error("Sheet name not found. Please check spelling and capitalization.")



    else:
        st.markdown("## Incorrect Password. Please try again.")
        st.stop()

def init_state():
    """Function that initializes the states used to check whether the next step of data initialization should continue."""
    defaults = {
            "step": 0,
            "spreadsheet": None,
            "semester_sheet": None,
            "header_index": None,
            "semester_df": None,
            "which_term": None,
            "classes_built": False,
            "all_classes": None,
            "trackers": None,
            "all_students": None,
            "lesson_content": None,
            "curriculum_sheet": None,
            "cur_header_index": None,
            "curriculum_df": None,
            "curriculum_headers": None,
            "template_dict": None,
            "filename_dict": None,
            "dump_done": False,
            "dump_keys": None,
        }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def corrected_semester_data_initialization(organization_name, correct_password, bucket_name, client):
    """Corrected version of the other initialization function. This function executes all the functions used to initialize the data for a new organization.
       It requires a bucket to have already been made by the AWS S3 Administrator. It is provided by the user as text input."""
    init_state()
    if "dump_done" not in st.session_state:
        st.session_state.dump_done = False
    if "step" not in st.session_state:
        st.session_state.step = 8

    st.sidebar.title("Access")
    admin_password = st.sidebar.text_input("", type="password")

    if admin_password != correct_password:
        st.markdown("## Incorrect Password. Please try again.")
        return

    st.markdown("## Administrator Validated: Initialize Semester Data")
    step = st.session_state.step

    # -------------------------
    #step 0: uploading master spreadsheet
    # -------------------------
    if step == 0:
        st.markdown("### Upload your master organization .xlsx file")
        upload = st.file_uploader("", type=["xlsx"])
        if upload:
            st.session_state.spreadsheet = upload
            st.session_state.step = 1
            st.rerun()
        return

    # -------------------------
    #step 1: choosing semester sheet
    # -------------------------
    if step == 1:
        xls = pd.ExcelFile(st.session_state.spreadsheet)
        which_semester = st.selectbox("Choose the semester sheet:", xls.sheet_names)

        if st.button("Confirm"):
            st.session_state.semester_sheet = which_semester
            st.session_state.step = 2
            st.rerun()
        return

    # -------------------------
    #step 2: setting header index
    # -------------------------
    if step == 2:

        header_index = st.text_input("Header row index (0-based):")
        if header_index.isdigit():
            st.session_state.header_index = int(header_index)

            master_df = pd.read_excel(
                st.session_state.spreadsheet,
                sheet_name=st.session_state.semester_sheet,
                header=st.session_state.header_index
            )
            st.dataframe(master_df)
        else:
            st.info("Please enter a valid integer for the header row index.")

        if st.button("Confirm Header Index"):
            st.session_state.header_index = int(header_index)
            st.session_state.semester_df = master_df
            master_headers = [col for col in master_df.columns if pd.notna(col) and not str(col).startswith("Unnamed")]
            st.session_state.master_headers = master_headers
            st.session_state.step = 3
            st.rerun()
        return

    # -------------------------
    #step 3: reviewing semester data + provide term name
    # -------------------------
    if step == 3:
        st.write("### Confirm semester data looks correct:")
        st.write(st.session_state.semester_df)

        which_term = st.text_input("Enter the term name:")
        if st.button("Continue"):
            st.session_state.which_term = which_term
            st.session_state.step = 4
            st.rerun()
        return

    # -------------------------
    #step 4: building trackers
    # -------------------------
    if step == 4:
        df = st.session_state.semester_df
        st.dataframe(df)

        st.write("### Building class + student + instructor trackers...")
        built = build_student_trackers_and_instructors(df)

        if not built:
            st.error("Could not build trackers. Check data.")
            return

        classes, trackers, students = built
        st.session_state.all_classes = classes
        st.session_state.trackers = trackers
        st.session_state.all_students = students

        st.session_state.classes_built = True

        st.session_state.step = 5
        st.rerun()

    # -------------------------
    #step 5: uploading curriculum file
    # -------------------------
    if step == 5:
        st.write(st.session_state.all_students)
        st.markdown("### Upload curriculum .xlsx file")
        content = st.file_uploader("", type=["xlsx"], key="curr_upload")

        if content:
            st.session_state.lesson_content = content
            st.session_state.step = 6
            st.rerun()
        return

    # -------------------------
    # STEP 6: Choose curriculum sheet
    # -------------------------
    if step == 6:
        xls = pd.ExcelFile(st.session_state.lesson_content)
        which_curr = st.selectbox("Choose curriculum sheet:", xls.sheet_names)

        if st.button("Confirm Curriculum Sheet"):
            st.session_state.curriculum_sheet = which_curr
            st.session_state.step = 7
            st.rerun()
        return

    # -------------------------
    #step 7: setting curriculum header index
    # -------------------------
    if step == 7:
        st.dataframe(pd.read_excel(st.session_state.lesson_content))
        cur_header_index = st.text_input("Curriculum header index (0-based):")

        if cur_header_index.isdigit():
            st.session_state.curriculum_header = int(cur_header_index)
            displayed_cur_df = pd.read_excel(
                st.session_state.lesson_content,
                sheet_name=st.session_state.curriculum_sheet,
                header=st.session_state.curriculum_header
            )
            st.dataframe(displayed_cur_df)


        if st.button("Confirm Curriculum Header"):
            st.session_state.cur_header_index = int(cur_header_index)

            df = pd.read_excel(
                st.session_state.lesson_content,
                sheet_name=st.session_state.curriculum_sheet,
                header=st.session_state.cur_header_index
            )
            st.session_state.curriculum_df = df

            # filter unnamed headers
            headers = [
                col for col in df.columns
                if pd.notna(col) and not str(col).startswith("Unnamed")
            ]
            st.session_state.curriculum_headers = headers

            st.session_state.step = 8
            st.rerun()
        return

    # -------------------------
    #step 8: configuring template and building curriculum trackers
    # -------------------------
    if step == 8:

        #only call builder if not already built
        if "built_curriculum" not in st.session_state:
            st.session_state["built_curriculum"] = None

        if st.session_state.get("built_curriculum") is None:
            #this will return the deserialized curriculum (dict) or None while user is still interacting
            st.write("### Confirm curriculum page looks correct:")
            result = build_curriculum_tracker(st.session_state.curriculum_df)
            if result:
                st.session_state["built_curriculum"] = result

        #now check both template_config and build result
        if st.session_state.get("built_curriculum") and st.session_state.get("curriculum_headers"):
            template_config = initialize_and_configure_template(st.session_state.curriculum_headers)
            if template_config:
                st.session_state.template_dict = template_config[4]
                st.session_state.step = 9
                return

    # -------------------------
    # Step 9: Getting filenames from user
    # -------------------------
    if step == 9:
        filename_dict = get_filenames_from_user()
        if filename_dict:
            st.session_state.filename_dict = filename_dict
            st.session_state.step = 10
            st.rerun()


    # -------------------------
    # Step 10: Final dump so S3
    # -------------------------
    if step == 10 and not st.session_state.dump_done:
        st.write("### Dumping semester data to AWS S3...")



        keys = dump_semester_data_aws(
            {class_name: the_class.unpack_class_object() for class_name, the_class in st.session_state.all_classes.items()},
            {instructor_name: instructor_object.unpack_instructor_object() for instructor_name, instructor_object in st.session_state.trackers.items()},
            {student_name: student_object.unpack_student() for student_name, student_object in st.session_state.all_students.items()}, #this is the one messed up line bc of pandas series somewhere....
            st.session_state.built_curriculum,
            st.session_state.template_dict,
            organization_name,
            st.session_state.which_term,
            bucket_name,
            client,
            st.session_state.filename_dict
        )
        st.session_state.dump_keys = keys

        st.success("✅ Data successfully initialized!")
        st.session_state.dump_done = True
        return True

def initialize_and_configure_template(dataframe_headers):
    """Function that receives an uploaded template used for weekly reports,
    figures out how to associate each section of the template with the corresponding pages covered/daily homework assignment
    as given in the curriculum data, and outputs a jinja template used when instructors actually calling
    the report making function themselves.
    """

    env = Environment()
    env.filters["fix_series_format"] = fix_series_format

    if "header_chosen" not in st.session_state:
        st.session_state["header_chosen"] = False

    st.markdown("## You must now upload the template (as a word doc) you would like to use for weekly reports/homework assignments. Note that there should be a whitespace (enter) between each section of the template.")
    raw_template = st.file_uploader("", type="docx",key = "Raw Template" )
    if raw_template:
        headers_to_sections_map = {}
        groupings = {}
        if raw_template is not None:
            template_doc_object = docx.Document(raw_template)
            sections = [paragraph.text for paragraph in template_doc_object.paragraphs if paragraph.text != ""]
            st.markdown("### These are the sections, if they look good, continue. otherwise, reupload the file. You may not duplicate a header.")
            st.write(sections)

            options_right = dataframe_headers.copy()
            options_right.insert(0, None)


            #this is the part where the sections are matched to headers of the dataframe
            for i, section in enumerate(sections):
                text_to_ask = "Which header corresponds to the section {actual_section}? The answer can be None.".format(actual_section = section)
                st.markdown("#### " + text_to_ask)
                which_header_goes = st.radio(label = "", options = options_right, key = text_to_ask + str(i), horizontal=True) #not working for some reason
                headers_to_sections_map[section.strip()] =  (which_header_goes)

            st.markdown("## Name the sections that are supposed to be grouped together, separated by a semicolon.")
            raw_groupings = st.text_input("", key = "first raw groupings")
            if raw_groupings:

                    split_groupings = raw_groupings.split(";")

                    stripped_sections = [section.strip() for section in sections]

                    st.markdown("#### Which header corresponds to the one that instructors will input data on?")
                    which_header_instructor_input = st.radio(
                        "", options_right, horizontal = True)

                    if st.button("Continue", key="here continue"):
                        st.session_state["header_chosen"] = True

                    if st.session_state["header_chosen"]:
                        st.success("Continue was clicked — now running the next section.")
                        all_group_indices = []
                        for grouping in split_groupings:

                            separated_grouping = grouping.split(",")
                            cleaned_separated_grouping = [piece.strip() for piece in separated_grouping]
                            first_grouping_section = cleaned_separated_grouping[0]


                            grouping_indices = [stripped_sections.index(subsection) for subsection in cleaned_separated_grouping] #keeping track of where the grouped elements are for later
                            for single_grouped_index in grouping_indices:
                                all_group_indices.append(single_grouped_index)

                            fixed_groupings = []

                            for grouped_index in grouping_indices: #for finding out which sections won't be grouped later
                                # determining if an index corresponds to the data entry one
                                is_data_entry = False
                                if headers_to_sections_map[stripped_sections[grouped_index]]  ==  which_header_instructor_input:
                                    is_data_entry = True
                                fixed_groupings.append([grouped_index, is_data_entry])


                            groupings[first_grouping_section] = fixed_groupings

                        for any_index in range(0, len(sections)):
                            not_data_entry = False
                            if any_index not in all_group_indices:
                                groupings[stripped_sections[any_index]] = [[any_index, not_data_entry]]
                        sorted_groupings = dict(sorted(groupings.items(), key = lambda these: these[1][0][0])) #sorting groupings for later template generation

                        template_pieces = []
                        for grouping in sorted_groupings.values():
                            if len(grouping) != 1:  # section duplicated once per student
                                template_pieces.append("{% for student_name, student_data in data.items() %}")
                                template_pieces.append("*{{ student_name.rstrip() }}*")  # fix 1
                                template_pieces.append("\n") #fix 2
                                for subsection_index, data_entry_header in grouping:
                                    which_section = sections[subsection_index].strip()
                                    if data_entry_header:
                                        template_pieces.append(
                                            sections[subsection_index]
                                            + " "
                                            + "{{ student_pages_covered[student_name] }}"
                                        )
                                    else:
                                        template_pieces.append(sections[subsection_index] + " " +  f"{{{{ student_data['{which_section.rstrip()}'] | fix_series_format }}}}")
                                    template_pieces.append("\n")
                                template_pieces.append("{% endfor %}")
                            else:  # no duplication
                                for nongrouped_subsection_index, unneeded_boolean in grouping:
                                    template_pieces.append(f"**{sections[nongrouped_subsection_index].rstrip()}**")
                            template_pieces.append("\n")
                            template_pieces.append("\n")

                        actual_template_string = "\n".join(template_pieces)
                        #saving all template pieces to a dict for later use
                        all_template_pieces_dict = {}
                        all_template_pieces_dict["headers_to_sections_map"] = headers_to_sections_map
                        all_template_pieces_dict["which_header_instructor_input"] = which_header_instructor_input
                        all_template_pieces_dict["sorted_groupings"] = sorted_groupings
                        all_template_pieces_dict["actual_template_string"] = actual_template_string


                        return headers_to_sections_map, which_header_instructor_input, sorted_groupings, actual_template_string, all_template_pieces_dict
        else:
            st.info("Waiting for your input.")

def get_filenames_from_user():
    """Simple function to get all the names of the files the user wants to name the
    semester class data, instructor tracker data, all student data, curriculum data, and template data."""
    filename_dict = {}


    st.markdown("## How would you like the class data for this semester to be named?")
    semester_data_filename = st.text_input("", key = "cdf")
    filename_dict["semester_class_data_filename"] = semester_data_filename


    st.markdown("## How would you like the instructor tracker data for this semester to be named?")
    instructor_tracker_filename = st.text_input("", key = "tdf")
    filename_dict["semester_instructor_trackers_filename"] = instructor_tracker_filename


    st.markdown("## How would you like permanent student data to be named?")
    student_data_filename = st.text_input("", key = "sdf")
    filename_dict["all_student_data_filename"] = student_data_filename


    st.markdown("## How would you like the curriculum data to be named?")
    curriculum_data_filename = st.text_input("", key = "curdf")
    filename_dict["curriculum_data_filename"] = curriculum_data_filename


    st.markdown("## How do you want the template to be named?")
    template_data_filename = st.text_input("", key = "temdf")
    filename_dict["template_filename"] = template_data_filename

    if all([semester_data_filename, instructor_tracker_filename, student_data_filename, curriculum_data_filename, template_data_filename]):
        return {
            "semester_class_data_filename": semester_data_filename,
            "semester_instructor_trackers_filename": instructor_tracker_filename,
            "all_student_data_filename": student_data_filename,
            "curriculum_data_filename": curriculum_data_filename,
            "template_filename": template_data_filename,
        }
    else:
        st.info("You have not entered a name in each field yet.")

# def dump_semester_data(all_classes, all_instructors, all_students, all_curriculum, template_dict, new_directories, the_filename_dict):
#     """This function dumps the data from AClass and AnInstructor objects into jsons
#     for cross-session persistence of data. The Jsons will be stored in the directories built at the beginning of the
#     initialization session for now. But later, they will be stored in some S3 or other server."""
#     semester_class_data_filename = the_filename_dict["semester_class_data_filename"]
#     semester_instructor_trackers_filename = the_filename_dict["semester_instructor_trackers_filename"]
#     all_student_data_filename = the_filename_dict["all_student_data_filename"]
#     curriculum_data_filename = the_filename_dict["curriculum_data_filename"]
#     template_filename = the_filename_dict["template_filename"]
#
#     #this is saving the classes and all of the students in them to a json
#     base_directory = new_directories[0]
#     all_paths_json_dir = base_directory + "/" + "all_paths.json"  #This is what is used for retrieval later
#     parsed_directory = new_directories[1] #unused now
#     raw_files_directory = new_directories[2] #unused now
#     student_files_directory  = new_directories[3]
#     instructors_files_directory = new_directories[4]
#     curriculum_files_directory = new_directories[5]
#     class_files_directory = new_directories[6]
#     template_directory = new_directories[7]
#
#     full_path_student_data = os.path.join(student_files_directory,all_student_data_filename)
#     full_path_class_data = os.path.join(class_files_directory,semester_class_data_filename)
#     full_path_instructor_trackers = os.path.join(instructors_files_directory,semester_instructor_trackers_filename)
#     full_path_curriculum_tracker = os.path.join(curriculum_files_directory, curriculum_data_filename)
#     full_path_template = os.path.join(template_directory, template_filename)
#     """IMPORTANT: Below lines are used for dumping the directories of the instructor and tracker into its own json that is
#     present in the base directory where the organization's data is kept.
#     This allows for the efficient retrieval of the class data, since the user decided what to name it, and that goes into
#     the name of the directory containing the trackers and instructor data."""
#     all_paths_dict = {"Class Data": full_path_class_data, "Instructor/Tracker Data": full_path_instructor_trackers, "Curriculum Data": full_path_curriculum_tracker,
#                       "Template": full_path_template}
#
#     with open(all_paths_json_dir, "w") as directory_data:
#         json.dump(all_paths_dict, directory_data, indent = 4)
#
#     #dumping all student data
#     with open(full_path_student_data, "w") as student_data:
#         json.dump(all_students, student_data, indent = 4)
#
#     #dumping all class data into a json
#     with open(full_path_class_data, "w") as class_data:
#         json.dump(all_classes, class_data, indent = 4)
#
#     # dumping all instructor data into a json
#     with open(full_path_instructor_trackers, "w") as instructor_data:
#         json.dump(all_instructors, instructor_data, indent=4)
#
#     #dumping all curriculum data into a json
#     with open(full_path_curriculum_tracker, "w") as curr_data:
#         json.dump(all_curriculum, curr_data, indent = 4)
#
#     #dumping the template data pieces dict into a json
#     with open(full_path_template, "w") as template_data:
#         json.dump(template_dict, template_data)
#
#     #ends by returning all of the directories that jsons have been written to so that session state can save them (not used)
#     return full_path_class_data, full_path_instructor_trackers, full_path_curriculum_tracker, full_path_template

def dump_semester_data_aws(all_classes, all_instructors, all_students, all_curriculum, template_dict, organization_name, which_term, bucket_name, client, the_filename_dict):
    """This function is used to dump all semester data (class data, instructor trackers, student data, curriculum and
     template data) into the master S3 bucket that has already been created. Prefixes are made using the
     existing organization name that the admin just created."""

    semester_class_data_filename = the_filename_dict["semester_class_data_filename"]
    semester_instructor_trackers_filename = the_filename_dict["semester_instructor_trackers_filename"]
    all_student_data_filename = the_filename_dict["all_student_data_filename"]
    curriculum_data_filename = the_filename_dict["curriculum_data_filename"]
    template_filename = the_filename_dict["template_filename"]

    # Define "prefixes" like folders in S3
    base_prefix = f"{organization_name}/data/{which_term}/"
    student_prefix = f"{base_prefix}students/"
    instructor_prefix = f"{base_prefix}instructors/"
    class_prefix = f"{base_prefix}classes/"
    curriculum_prefix = f"{base_prefix}curriculum/"
    template_prefix = f"{base_prefix}templates/"

    #All "keys" (paths in the bucket)
    student_key = student_prefix + all_student_data_filename
    class_key = class_prefix + semester_class_data_filename
    instructor_key = instructor_prefix + semester_instructor_trackers_filename
    curriculum_key = curriculum_prefix + curriculum_data_filename
    template_key = template_prefix + template_filename
    #the all paths dict will be saved to a key that only contains the organization info for simple retrieval by an instructor user later
    all_paths_key = f"{organization_name}/data/" +  "all_paths.json"


    # Index file to help retrieval later (this defines the main directory used to access different organization data)
    all_paths_dict = {
        "Class Data": class_key,
        "Instructor/Tracker Data": instructor_key,
        "Curriculum Data": curriculum_key,
        "Template": template_key,
        "Students": student_key
    }

    #uploading all jsons
    client.put_object(Bucket = bucket_name, Body = json.dumps(all_paths_dict), Key = all_paths_key)
    client.put_object(Bucket=bucket_name, Body=json.dumps(all_students), Key=student_key)
    client.put_object(Bucket=bucket_name, Body=json.dumps(all_classes), Key=class_key)
    client.put_object(Bucket=bucket_name, Body=json.dumps(all_instructors), Key=instructor_key)
    client.put_object(Bucket = bucket_name, Body = json.dumps(all_curriculum), Key = curriculum_key)
    client.put_object(Bucket = bucket_name, Body = json.dumps(template_dict), Key = template_key)

    st.markdown("## (AWS) Data initialization complete!")

    # ends by returning the keys that jsons have been written to so that session state can save them (not used)
    return class_key, instructor_key, curriculum_key, template_key

def deserialize_curriculum_data(organization_levels_and_material_dict):
    #converting each dataframe in the organization's levels and material dict into json dumpable dictionaries
    deserialized_sublevels_dict = {}

    for level, sublevels_dict in organization_levels_and_material_dict.items():
        st.write(sublevels_dict)
        deserialized_sublevel_dict = {sublevel: sublevel_frame.to_dict(orient="records") for sublevel, sublevel_frame in sublevels_dict.items()}
        deserialized_sublevels_dict[level] = deserialized_sublevel_dict

    return deserialized_sublevels_dict

def reinitialize_template(organization_name, this_client, this_bucket):
    here_all_paths_key = f"{organization_name}/data/" + "all_paths.json"
    loaded_all_paths = load_json_from_S3(this_client, this_bucket, here_all_paths_key)[0]
    curriculum_data_key = loaded_all_paths["Curriculum Data"]
    old_template_data_key = loaded_all_paths["Template"]
    loaded_curriculum_data = load_json_from_S3(this_client, this_bucket, curriculum_data_key)
    the_old_dataframe_headers = list(list(  list   (list(loaded_curriculum_data[0].values())[0].values())[0])[0].keys()) #perhaps the easiest way to do this, but it's assuming the section headers are the same

    new_template_configured = initialize_and_configure_template(the_old_dataframe_headers)
    if new_template_configured:
        new_template_dict = new_template_configured[4]
        this_client.put_object(Bucket=this_bucket, Body=json.dumps(new_template_dict), Key=old_template_data_key)
        st.markdown("## Template Updated. The old template has been erased.")

def assign_location_names_to_class_codes(organization_name, this_client, this_bucket):
    """**Currently unused**. Assigns location to each class code. Is manual right now, allowing for abbreviations
    that might be useful later. But will later be edited to get this information from the spreadsheet."""

    class_code_to_location_map = {}
    here_all_paths_key = f"{organization_name}/data/" + "all_paths.json"
    loaded_all_paths = load_json_from_S3(this_client, this_bucket, here_all_paths_key)[0]

    class_data_key = loaded_all_paths["Class Data"]

    loaded_class_data = set(load_json_from_S3(this_client, this_bucket, class_data_key)[0].keys())
    class_data_keys_list = list(loaded_class_data)

    class_data_keys_list.sort()

    #using group by to annotate groups of class codes at once for more efficient naming
    grouped_sorted_class_data = [list(location) for _, location in groupby(class_data_keys_list, lambda k: k[0])]

    st.write("Below, please reuse the same names exactly, or errors will be encountered later.")
    for group in grouped_sorted_class_data:
        prefix = group[0].split("-")[0]
        formatted_ask_string = "Which location corresponds to name {}?".format(prefix)
        which_name_corresponds = st.text_input(formatted_ask_string)

        for code in group:
            class_code_to_location_map[code] = which_name_corresponds

    #updating the all_paths_json
    which_term = st.text_input("What is the current term? This must match the other ones you used.")

    #using the same base prefix
    base_prefix = f"{organization_name}/data/{which_term}/"

    key_for_map = base_prefix + "Location Map"

    loaded_all_paths["Location Map"] = key_for_map


    #placing the map
    this_client.put_object(Bucket=this_bucket, Body=json.dumps(class_code_to_location_map), Key=key_for_map)

    # overwriting the all_paths with the updated one
    this_client.put_object(Bucket = this_bucket, Body = json.dumps(loaded_all_paths), Key = here_all_paths_key)
    st.write("Updating Complete")

def assign_students_to_new_classes(organization_name, this_client, this_bucket):
    """Function used by admin to assign students to classes, sorting by level, previous instructor,
    and student availability."""

    if "edited_group_dfs" not in st.session_state:
        st.session_state.edited_group_dfs = {}
    if "new_term_class_data_dict" not in st.session_state:
        st.session_state.new_term_class_data_dict = {}

    student_level_availability_dict = {}
    raw_instructor_availabilities = st.file_uploader("Please upload a spreadsheet containing instructors' availabilities as a MS Excel File.", type="xlsx")

    raw_student_availabilities_locations_and_levels = st.file_uploader("Please upload a spreadsheet containing students' availabilities and current levels as a MS Excel File.", type="xlsx")


    if raw_instructor_availabilities and raw_student_availabilities_locations_and_levels:
        student_availabilities = pd.ExcelFile(raw_student_availabilities_locations_and_levels)
        instructor_availabilities = pd.ExcelFile(raw_instructor_availabilities)
        df_instructor_availabilities = pd.read_excel(instructor_availabilities)
        df_student_availabilities = pd.read_excel(student_availabilities, header = 1) #change to be dynamic later

        which_header_student = st.text_input("Please type the header in the student availability sheet which corresponds "
                                             "to the students' names.")
        which_header_location = st.text_input("Please type the header in the student availability sheet which corresponds "
                                             "to the students' locations.")
        which_header_availability = st.text_input("Please type the header in the student availability sheet which corresponds "
                                             "to the students' actual availabilities.")

        which_header_instructor_name = st.text_input("Please type the header in the instructor availability sheet which corresponds "
                                             "to the instructors' actual names.")

        which_header_instructor_availability = st.text_input("Please type the header in the instructor availability sheet which corresponds "
                                             "to the instructors' actual availabilities.")

        if which_header_student and which_header_location and which_header_availability and which_header_instructor_name and which_header_instructor_availability:
            these_retained_headers = [which_header_student, which_header_availability, which_header_location]
            these_retained_headers_instructors = [which_header_instructor_name, which_header_instructor_availability]
            retained_headers_dict = {"which_header_student": which_header_student, "which_header_location": which_header_location,
                                     "which_header_availability": which_header_availability}
            retained_instructor_headers_dict = {"which_header_instructor_name": which_header_instructor_name, "which_header_instructor_availability": which_header_instructor_availability}
            #retrieving student data from S3
            here_all_paths_key = f"{organization_name}/data/" + "all_paths.json"
            loaded_all_paths = load_json_from_S3(this_client, this_bucket, here_all_paths_key)[0]

            student_data_key = loaded_all_paths["Students"]
            student_data = load_json_from_S3(this_client, this_bucket, key=student_data_key)[0]

            repacked_students = {}
            for student_name, unpacked_student in student_data.items():
                repacked_students[student_name] = Student.repack_student(unpacked_student)

            #retrieving current instructor data from S3
            instructor_data_key = loaded_all_paths["Instructor/Tracker Data"]
            instructor_data = load_json_from_S3(this_client, this_bucket, key=instructor_data_key)[0]
            repacked_instructors = {}
            repacked_instructors_and_their_students = {}

            for instructor_name, unpacked_classes in instructor_data.items():
                repacked_classes = []
                just_the_students = []

                for this_class_ID, one_of_their_classes_unpacked in unpacked_classes.items():
                    that_repacked_class = AClass.repack_class_object(class_ID = this_class_ID, deserialized_dict= one_of_their_classes_unpacked)
                    #just grabbing the students in each class (can be changed later)
                    for ind_student in that_repacked_class.students:
                        just_the_students.append(ind_student)
                    repacked_classes.append(that_repacked_class)

                repacked_instructors[instructor_name] = repacked_classes
                repacked_instructors_and_their_students[instructor_name] = just_the_students


            #iterating over all repacked students to start building the student level availability dict
            for student_name, repacked_student in repacked_students.items():
                student_relevant_data = [student_name] #this is redundant but neccesary to be consistent with the grouping function logic used later
                if repacked_student is not None:

                    #searching for the student's availability in the dataframe above, referencing the retained headers
                    for index, inner_student_name in enumerate(df_student_availabilities[retained_headers_dict["which_header_student"]].tolist()):
                        if inner_student_name is not "":
                            if student_name == inner_student_name:
                                students_availability = df_student_availabilities[retained_headers_dict["which_header_availability"]].tolist()[index]
                                student_location = df_student_availabilities[retained_headers_dict["which_header_location"]].tolist()[index]

                                student_relevant_data.append(students_availability)
                                student_relevant_data.append(student_location)


                    students_level_current = repacked_student.level[
                        len(repacked_student.level) - 1]  #adding student level to current data
                    student_relevant_data.append(students_level_current)
                #searching for their current instructor and adding to relevant data
                for instructor, their_students in repacked_instructors_and_their_students.items():
                    if student_name in their_students:
                        student_relevant_data.append(instructor)

                student_level_availability_dict[student_name] = student_relevant_data

            #removing any nans or otherwise
            student_availability_other_data_dict_fixed = {}

            #important note: the order of relevant student data is data corresponding to the retained headers, THEN their current level and current instructor.
            for again_name, relevant_data in student_level_availability_dict.items():
                #this is currently hardcoded, respecting the number of retained headers and exactly 2 other attributes (current level/instructor)
                #organizations that would want to have more than 2 other attributes than the ones above would require refactoring. for now, we present this version
                if len(relevant_data) == len(these_retained_headers) + 2:
                    student_availability_other_data_dict_fixed[again_name] = relevant_data

            sorted_availability_fixed_dict = dict(sorted(student_availability_other_data_dict_fixed.items(),
                                       key = lambda item: ((item[1][3], item[1][0]))))


            #actually letting them assign students to classes, based on sorting
            #for grouping to proceed correctly, retained_headers must be modified in place to add the student current level and instructor as columns of resulting dataframes
            #see above if organizations want to have more than 2 other attributes.
            these_retained_headers.extend(["Current Level", "Current Instructor"])
            grouped = group_dict_to_dataframes_by_index(sorted_availability_fixed_dict, 3, these_retained_headers)

            #here, instructor availability is appended to each dataframe in grouped for convenience
            df_instructor_availabilities = pd.read_excel(instructor_availabilities)

            fixed_grouped = {}
            for level, sorted_frame in grouped.items():

                new_column = []
                for current_instructor in sorted_frame["Current Instructor"]:
                    try:
                        that_instructors_availability_index = df_instructor_availabilities.index[df_instructor_availabilities[retained_instructor_headers_dict["which_header_instructor_name"]] == current_instructor].tolist()[0]
                        that_instructor_avail = df_instructor_availabilities.loc[
                            that_instructors_availability_index, retained_instructor_headers_dict[
                                "which_header_instructor_availability"]]
                        new_column.append(that_instructor_avail)
                    except IndexError: #in case the instructor's data either isn't in the system or the instructor was deleted from it
                        new_column.append("No availability for the previous instructor")



                sorted_frame["Previous Instructors' Availability"] = new_column
                fixed_frame = sorted_frame
                fixed_grouped[level] = fixed_frame


            #initializing the currently assigned students
            if "new_term" not in st.session_state:
                st.session_state.new_term = ""

            st.session_state.new_term = st.text_input(
                "Name the term for the new classes.",
                value=st.session_state.new_term,  # persist across reruns
                key="New_Term_Input"
            )
            new_term = st.session_state.new_term.strip()

            #loading currently assigned students
            try:
                assigned_students_key = loaded_all_paths.get("Currently Assigned Students")
                if not assigned_students_key:
                    raise KeyError("Currently Assigned Students key missing or empty")

                response = this_client.get_object(Bucket=this_bucket, Key=assigned_students_key)
                currently_assigned_students = json.loads(response["Body"].read())

            except (ClientError, KeyError) as e:
                if isinstance(e, ClientError) and e.response['Error']['Code'] == "NoSuchKey":
                    st.warning("No 'Currently Assigned Students' object found in S3. Initializing an empty list.")
                else:
                    st.warning("No 'Currently Assigned Students' key found in all_paths. Initializing empty list.")
                currently_assigned_students = []

            #Buttons
            go_on_button = st.button("Create Class")
            done_button = st.button("Done Creating Classes")

            #Stops running early if no term entered
            if not new_term:
                st.info("Enter a term name above before creating or saving classes.")
                st.stop()

            #Sanity check
            st.write(f"Saving classes for term: **{new_term}**")
            st.info("Make sure to write a name for the new class and assign an instructor (scroll to the bottom) before clicking Create Class.")
            # Initialize session dicts
            if "edited_group_dfs" not in st.session_state:
                st.session_state.edited_group_dfs = {}
            if "new_term_class_data_dict" not in st.session_state:
                st.session_state.new_term_class_data_dict = {}

            #3 columns for editable tables
            cols = st.columns([1.5, 1.5, 1.5])

            # Loop through each group and display editable table
            for i, (group, df) in enumerate(fixed_grouped.items()):
                col = cols[i % 3]  # cycle through 3 columns
                with col:
                    df = df.copy()
                    df.columns = df.columns.map(str)  # flatten headers

                    #determining student column
                    student_col = which_header_student

                    #making sure checkbox column exists
                    if "Add to a New Class" not in df.columns:
                        if student_col in df.columns:
                            df["Add to a New Class"] = df[student_col].isin(currently_assigned_students)
                        else:
                            st.warning(
                                f"Could not find student column '{student_col}' in group '{group}'. Initializing unchecked column.")
                            df["Add to a New Class"] = False

                    #placing checkbox column at the end
                    df = df[[c for c in df.columns if c != "Add to a New Class"] + ["Add to a New Class"]]

                    #editing table
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Add to a New Class": st.column_config.CheckboxColumn(
                                "Add to a New Class",
                                help="Check to include this student in the new class."
                            )
                        },
                        num_rows="fixed",
                        key=f"editor_{group}",
                        use_container_width=True
                    )

                    #restoring headers
                    edited_df.columns = df.columns

                    #saving edited dataframe
                    st.session_state.edited_group_dfs[group] = edited_df

            #combining all edited groups safely
            if st.session_state.edited_group_dfs:
                all_edited = pd.concat(st.session_state.edited_group_dfs.values(), ignore_index=True)

                #striping whitespace from column names if needed
                all_edited.columns = all_edited.columns.str.strip()

                #forcing checkbox column to be appeneded if missing
                if "Add to a New Class" not in all_edited.columns:
                    all_edited["Add to a New Class"] = False

                #filtering safely
                selected_rows = all_edited[all_edited["Add to a New Class"] == True]
                remaining_rows = all_edited[all_edited["Add to a New Class"] == False]

                # Moving selected to bottom
                new_df = pd.concat([remaining_rows, selected_rows], ignore_index=True)
            else:
                all_edited = pd.DataFrame()
                selected_rows = pd.DataFrame()
                remaining_rows = pd.DataFrame()
                new_df = all_edited.copy()

            # Show live DataFrame
            st.dataframe(new_df, use_container_width=True)

            # Inputs for new class creation
            class_name = st.text_input("Provide a code for the new class.", key="class_name_input")
            which_instructor = st.selectbox(
                "Choose an instructor for the class.",
                list(repacked_instructors_and_their_students.keys())
            )

            #allowing class creation if students selected
            if go_on_button:
                if selected_rows.empty:
                    st.warning("No students selected for this class.")
                else:
                    students_selected = selected_rows[which_header_student]
                    new_class_object = AClass(
                        class_ID=class_name,
                        instructor=which_instructor,
                        students=students_selected.tolist()
                    )
                    st.session_state.new_term_class_data_dict[class_name] = new_class_object
                    st.success(f"✅ Created class {class_name} with {len(students_selected)} students.")


    else:
        st.info("Waiting for your input.")

def main():
    """
    This function contains the main logic of the script.
    """
    # figuring out whether or not the user is from a tutoring group/organization that has already been logged
    st.set_page_config(layout="wide")
    st.markdown("## Welcome! Please enter your organization name.")
    this_organization_name = st.text_input("", key = 1)

    if this_organization_name:
        this_s3_client = boto3.client("s3")
        this_bucket_name = "classandlessontrackingplatform-testing-data"
        passwords_key = "Passwords/AllPasswords1110.json" #app owner has to input this
        retrieved_passwords_dict, this_passwords_dict_etag = load_json_from_S3(this_s3_client, this_bucket_name, passwords_key)
        try:
            this_correct_password = retrieved_passwords_dict[this_organization_name]

        except KeyError:
            st.markdown("## A password has not been created for your organization yet. Please contact the app administrators.")
            st.stop()

        do_we_initialize = not does_group_exist_yet_aws(this_organization_name, this_bucket_name, this_s3_client)



        if do_we_initialize:
            #this_initialization = semester_data_initialization(this_organization_name, this_bucket_name, this_s3_client, this_correct_password)
            this_corrected_initialization = corrected_semester_data_initialization(this_organization_name, this_correct_password, this_bucket_name, this_s3_client)
            if this_corrected_initialization:
                st.session_state["do_we_initialize"] = False
                st.session_state["did_we_initialize"] = True
            


        else:
            st.markdown("## Data is already initialized.")
            st.session_state["did_we_initialize"] = True
            st.session_state["do_we_initialize"] = False

            other_sidebar = st.sidebar.title("Access")
            here_admin_password = other_sidebar.text_input("Enter admin password to proceed to initialization/administrator features.",
                                                        type="password")

            if here_admin_password == this_correct_password:
                st.title("Administrator Validated!")

                action_options = ["Re-Initialize Template", "Assign Existing Students to New Term Classes", "Other"]
                chosen_option = st.radio("What would you like to do?", options=action_options)

                if chosen_option == "Re-Initialize Template":
                    this_reinitialized_template = reinitialize_template(this_organization_name, this_s3_client, this_bucket_name)


                if chosen_option == "Assign Existing Students to New Term Classes":
                    new_assignment = assign_students_to_new_classes(this_organization_name, this_s3_client, this_bucket_name)

                #location_of_json_dirs = os.path.join(os.getcwd(), this_organization_name, "data", "all_paths.json")

                # with open(location_of_json_dirs, 'r') as f:
                #     directories_dict = json.load(f)
                #
                # st.session_state["class_data_dir"] = os.path.join(os.getcwd(), directories_dict["Class Data"])
                # st.session_state["instructor_data_dir"] = os.path.join(os.getcwd(), directories_dict["Instructor/Tracker Data"])
                # st.session_state["curriculum_data_dir"] = os.path.join(os.getcwd(), directories_dict["Curriculum Data"])
                # st.session_state["template"] = os.path.join(os.getcwd(), directories_dict["Template"])
    else:
        pass

if __name__ == "__main__":
    main()


