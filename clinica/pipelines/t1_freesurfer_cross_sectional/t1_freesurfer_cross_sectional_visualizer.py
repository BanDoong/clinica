# coding: utf8

import clinica.engine as ce


class T1FreeSurferVisualizer(ce.CmdParser):

    def define_name(self):
        """Define the sub-command name to run this pipelines.
        """
        self._name = 't1-freesurfer'

    def define_description(self):
        """Define a description of this pipeline.
        """
        self._description = 'Cross-sectional pre-processing of T1w images with FreeSurfer:\nhttp://clinica.run/doc/Pipelines/T1_FreeSurfer/'

    def define_options(self):
        """Define the sub-command arguments
        """
        from clinica.engine.cmdparser import PIPELINE_CATEGORIES

        clinica_comp = self._args.add_argument_group(PIPELINE_CATEGORIES['CLINICA_COMPULSORY'])
        clinica_comp.add_argument("caps_directory",
                                  help='Path to the CAPS directory.')
        clinica_comp.add_argument("participant_id",
                                  help='Participant ID (e.g. sub-CLNC01).')
        clinica_comp.add_argument("session_id",
                                  help='Session ID (e.g. sub-M00).')

    def run_command(self, args):
        """
        """
        import os
        from clinica.utils.stream import cprint
        from clinica.utils.check_dependency import check_freesurfer
        import subprocess

        check_freesurfer()

        participant_id = args.participant_id
        session_id = args.session_id
        subject_id = participant_id + '_' + session_id

        cprint('Visualizing outputs of t1-freesurfer pipeline for ' + participant_id + ' at session ' + session_id)
        caps_participant = os.path.join(
            args.caps_directory, 'subjects', participant_id, session_id,
            't1', 'freesurfer_cross_sectional', subject_id
        )

        # Check that freesurfer has run properly
        log_file = os.path.join(caps_participant,
                                'scripts',
                                'recon-all-status.log')
        if os.path.isfile(log_file):
            last_line = str(subprocess.check_output(['tail', '-1', log_file]))
            if 'finished without error' not in last_line.lower():
                raise ValueError('FreeSurfer did not mark subject '
                                 + subject_id + ' as -finished without '
                                 + 'error-. If the pipeline is still running'
                                 + ', wait for it to finish. Otherwise, '
                                 + 'relaunch it.')
        else:
            raise FileNotFoundError('File ' + log_file + ' was not found. '
                                    + 't1-freesurfer must be run before '
                                    + 'using: clinica visualize t1-freesurfer')

        # Check that
        files = {'nu': os.path.join(caps_participant, 'mri', 'nu.mgz'),
                 'aseg': os.path.join(caps_participant, 'mri', 'aseg.mgz'),
                 'lhwhite': os.path.join(caps_participant, 'surf', 'lh.white'),
                 'lhpial': os.path.join(caps_participant, 'surf', 'lh.pial'),
                 'rhwhite': os.path.join(caps_participant, 'surf', 'rh.white'),
                 'rhpial': os.path.join(caps_participant, 'surf', 'rh.pial')}

        files_not_found = []
        for element in files:
            if not os.path.exists(files[element]):
                files_not_found.append(files[element])
        if len(files_not_found) > 0:
            error_string = 'The following file(s) has(ve) not been found :\n'
            for f in files_not_found:
                error_string = error_string + f + '\n'
            raise FileNotFoundError(error_string)

        command_line = \
            'freeview' \
            ' -v' \
            ' %s:name=T1w-nu-corrected' \
            ' %s:colormap=lut:opacity=0.2:name=segmentation' \
            ' -f' \
            ' %s:edgecolor=blue:name=left_white_surface' \
            ' %s:edgecolor=green:name=left_pial_surface' \
            ' %s:edgecolor=blue:name=righ_pial_surface' \
            ' %s:edgecolor=green:name=right_pial_surface' % \
            (files['nu'],
             files['aseg'],
             files['lhwhite'],
             files['lhpial'],
             files['rhwhite'],
             files['rhpial'])

        os.system(command_line)
