# coding: utf8


def init_input_node(caps_dir, participant_id, session_id, long_id, output_dir):
    """Initialize the pipeline."""
    import os
    import errno
    from clinica.utils.stream import cprint
    from clinica.utils.ux import print_begin_image

    # Extract <image_id>
    image_id = '{0}_{1}_{2}'.format(participant_id, session_id, long_id)

    # Create SUBJECTS_DIR for recon-all (otherwise, the command won't run)
    subjects_dir = os.path.join(output_dir, image_id)
    try:
        os.makedirs(subjects_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:  # EEXIST: folder already exists
            raise e

    # Create symbolic link containing cross-sectional segmentation in SUBJECTS_DIR so that recon-all can run
    cross_sectional_path = os.path.join(
        caps_dir,
        'subjects',
        participant_id,
        session_id,
        't1',
        'freesurfer_cross_sectional',
        participant_id + '_' + session_id
    )
    os.symlink(cross_sectional_path, os.path.join(subjects_dir, participant_id + '_' + session_id))
    cprint('Creating sym link from %s to %s' % (cross_sectional_path, subjects_dir))

    # Create symbolic links containing unbiased template in SUBJECTS_DIR so that recon-all can run
    template_path = os.path.join(
        caps_dir,
        'subjects',
        participant_id,
        long_id,
        'freesurfer_unbiased_template',
        participant_id + '_' + long_id
    )
    os.symlink(template_path, os.path.join(subjects_dir, participant_id + '_' + long_id))
    cprint('Creating sym link from %s to %s' % (template_path, subjects_dir))

    print_begin_image(image_id)

    return image_id, subjects_dir


def run_recon_all_long(subjects_dir,
                       participant_id,
                       session_id,
                       long_id,
                       directive):
    """Run recon-all to create a longitudinal correction of a time point.

    Note:
    Longitudinal correction with FreeSurfer expects arguments to follow this syntax:
    recon-all -long <tpN_id> <template_id> -all; e.g.: recon-all -long sub-CLNC01_ses-M00 sub-CLNC01_long-M00M18 -all

    Currently, Nipype does not provide interface for "recon-all -long" case. As a result, ReconAll interface should be
    modified to handle this situation. In the meantime, the arguments of this function follows ReconAll.inputs names
    namely:
        - "-long <tpN_id> <template_id>" is likely to be fed to ReconAll.inputs.args
        - "-all" will be fed to ReconAll.inputs.directive

    Folder containing the longitudinal correction has the following convention:
    <tpN_id>.long.<template_id>; e.g.: sub-CLNC01_ses-M00.long.sub-CLNC01_long-M00M18
    which is automatically generated by FreeSurfer.

    This folder name is likely to be retrieved in ReconAll.outputs.subject_id.

    See official documentation (https://surfer.nmr.mgh.harvard.edu/fswiki/LongitudinalProcessing) for details.
    """
    import subprocess
    from clinica.utils.stream import cprint

    # Prepare arguments for recon-all.
    flags = " -long {0}_{1} {0}_{2} ".format(participant_id, session_id, long_id)

    recon_all_long_command = 'recon-all {0} -sd {1} {2}'.format(flags, subjects_dir, directive)
    cprint(recon_all_long_command)
    subprocess_run_recon_all_long = subprocess.run(
        recon_all_long_command,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    if subprocess_run_recon_all_long.returncode != 0:
        raise ValueError('recon-all -long failed, returned non-zero code')

    subject_id = '{0}_{1}.long.{0]_{2}'.format(participant_id, session_id, long_id)

    return subject_id


def write_tsv_files(subjects_dir, subject_id):
    """
    Generate statistics TSV files in `subjects_dir`/regional_measures folder for `image_id`.

    Notes:
        We do not need to check the line "finished without error" in scripts/recon-all.log.
        If an error occurs, it will be detected by Nipype and the next nodes (i.e.
        write_tsv_files will not be called).
    """
    import os
    import datetime
    from colorama import Fore
    from clinica.utils.stream import cprint
    from clinica.utils.freesurfer import generate_regional_measures, extract_image_id_from_longitudinal_segmentation

    image_id = extract_image_id_from_longitudinal_segmentation(subject_id)
    if os.path.isfile(os.path.join(subjects_dir, subject_id, 'mri', 'aparc+aseg.mgz')):
        generate_regional_measures(subjects_dir, subject_id, "regional_measures", True)
    else:
        now = datetime.datetime.now().strftime('%H:%M:%S')
        cprint('%s[%s] %s | %s | %s does not contain mri/aseg+aparc.mgz file. '
               'Creation of regional_measures/ folder will be skipped.%s' %
               (Fore.YELLOW, now, image_id.participant_id, image_id.session_id, image_id.long_id, Fore.RESET))
    return image_id


def save_to_caps(subjects_dir, freesurfer_id, caps_dir, overwrite_caps=False):
    """Save the content of `subjects_dir` to CAPS folder.

    This function copies outputs of `subjects_dir` to
    `caps_dir`/subjects/<participant_id>/<session_id>/t1_freesurfer_cross_sectional/
    where `freesurfer_id` = <participant_id>_<session_id>.long.<participant_id>_<long_id>.
    The `source_dir`/`freesurfer_id`/ folder should contain the following elements:
        - fsaverage, lh.EC_average and rh.EC_average symbolic links
        - `freesurfer_id`/ folder containing the FreeSurfer segmentation
        - regional_measures/ folder containing TSV files
    Notes:
        We do not need to check the line "finished without error" in scripts/recon-all.log.
        If an error occurs, it will be detected by Nipype and the next nodes (including
        save_to_caps will not be called).
    Raise:
        FileNotFoundError: If symbolic links in `source_dir`/`image_id` folder are not removed
        IOError: If the `source_dir`/`image_id` folder does not contain FreeSurfer segmentation.
    """
    import os
    import datetime
    import errno
    import shutil
    from colorama import Fore
    from clinica.utils.stream import cprint
    from clinica.utils.ux import print_end_image
    from clinica.utils.freesurfer import extract_image_id_from_longitudinal_segmentation

    image_id = extract_image_id_from_longitudinal_segmentation(freesurfer_id)
    participant_id = image_id.participant_id
    session_id = image_id.session_id
    long_id = image_id.long_id

    destination_dir = os.path.join(
        os.path.expanduser(caps_dir),
        'subjects',
        participant_id,
        session_id,
        long_id,
        't1_freesurfer_longitudinal'
    )

    representative_file = os.path.join(freesurfer_id, 'mri', 'aparc+aseg.mgz')
    representative_source_file = os.path.join(os.path.expanduser(subjects_dir), freesurfer_id, representative_file)
    representative_destination_file = os.path.join(destination_dir, representative_file)
    if os.path.isfile(representative_source_file):
        # Remove symbolic links before the copy
        try:
            os.unlink(os.path.join(os.path.expanduser(subjects_dir), 'fsaverage'))
            os.unlink(os.path.join(os.path.expanduser(subjects_dir), 'lh.EC_average'))
            os.unlink(os.path.join(os.path.expanduser(subjects_dir), 'rh.EC_average'))
            os.unlink(os.path.join(os.path.expanduser(subjects_dir), participant_id + '_' + session_id))
            os.unlink(os.path.join(os.path.expanduser(subjects_dir), participant_id + '_' + session_id))

        except FileNotFoundError as e:
            if e.errno != errno.ENOENT:
                raise e

        if os.path.isfile(representative_destination_file):
            if overwrite_caps:
                shutil.rmtree(destination_dir)
            shutil.copytree(os.path.join(subjects_dir, freesurfer_id), destination_dir, symlinks=True)
            print_end_image(freesurfer_id)
    else:
        now = datetime.datetime.now().strftime('%H:%M:%S')
        cprint('%s[%s] %s does not contain mri/aseg+aparc.mgz file. '
               'Copy will be skipped.%s' %
               (Fore.YELLOW, now, freesurfer_id.replace('_', ' | '), Fore.RESET))

    return freesurfer_id
