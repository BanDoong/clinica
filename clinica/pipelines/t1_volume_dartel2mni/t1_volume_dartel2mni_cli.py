from typing import List, Optional, Tuple

import click

from clinica.pipelines import cli_param

pipeline_name = "t1-volume-dartel2mni"


@click.command(name=pipeline_name)
@cli_param.argument.bids_directory
@cli_param.argument.caps_directory
@cli_param.argument.group_label
@cli_param.option_group.pipeline_options
@cli_param.option.smooth
@cli_param.option_group.standard_options
@cli_param.option.subjects_sessions_tsv
@cli_param.option.working_directory
@cli_param.option.n_procs
@cli_param.option_group.advanced_options
@cli_param.option.tissues
@cli_param.option.modulate
@cli_param.option.voxel_size
def cli(
    bids_directory: str,
    caps_directory: str,
    group_label: str,
    smooth: List[int] = (8,),
    tissues: List[int] = (1, 2, 3),
    modulate: bool = False,
    voxel_size: Tuple[float, float, float] = (1.5, 1.5, 1.5),
    subjects_sessions_tsv: Optional[str] = None,
    working_directory: Optional[str] = None,
    n_procs: Optional[int] = None,
) -> None:
    """Register DARTEL template to MNI space.

    https://aramislab.paris.inria.fr/clinica/docs/public/latest/Pipelines/T1_Volume/
    """
    from networkx import Graph

    from clinica.utils.ux import print_end_pipeline

    from .t1_volume_dartel2mni_pipeline import T1VolumeDartel2MNI

    parameters = {
        "group_label": group_label,
        "tissues": tissues,
        "voxel_size": voxel_size,
        "modulate": modulate,
        "smooth": smooth,
    }

    pipeline = T1VolumeDartel2MNI(
        bids_directory=bids_directory,
        caps_directory=caps_directory,
        tsv_file=subjects_sessions_tsv,
        base_dir=working_directory,
        parameters=parameters,
        name=pipeline_name,
    )

    exec_pipeline = (
        pipeline.run(plugin="MultiProc", plugin_args={"n_procs": n_procs})
        if n_procs
        else pipeline.run()
    )

    if isinstance(exec_pipeline, Graph):
        print_end_pipeline(
            pipeline_name, pipeline.base_dir, pipeline.base_dir_was_specified
        )


if __name__ == "__main__":
    cli()
