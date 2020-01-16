import sys
from subprocess import call
from cytomine.models import Job
from neubiaswg5 import CLASS_SPTCNT
from neubiaswg5.helpers import NeubiasJob, prepare_data, upload_data, upload_metrics, get_discipline


def main(argv):
    # 0. Initialize Cytomine client and job if necessary and parse inputs
    with NeubiasJob.from_cli(argv) as nj:
        problem_cls = get_discipline(nj, default=CLASS_SPTCNT)
        is_2d = True
        nj.job.update(status=Job.RUNNING, progress=0, statusComment="Running workflow for problem class '{}' in {}D".format(problem_cls, 2 if is_2d else 3))

        # 1. Create working directories on the machine
        # 2. Download the images
        nj.job.update(progress=0, statusComment="Initialisation...")
        in_images, gt_images, in_path, gt_path, out_path, tmp_path = prepare_data(problem_cls, nj, is_2d=is_2d, **nj.flags)

        # 3. Call the image analysis workflow using the run script
        nj.job.update(progress=25, statusComment="Launching workflow...")
        command = "/usr/bin/xvfb-run java -Xmx6000m -cp /fiji/jars/ij.jar ij.ImageJ --headless --console " \
                  "-macro macro.ijm \"input={}, output={}, ij_radius={}, ij_noise={}\"".format(in_path, out_path, nj.parameters.ij_radius, nj.parameters.ij_noise)
        return_code = call(command, shell=True, cwd="/fiji")  # waits for the subprocess to return

        if return_code != 0:
            err_desc = "Failed to execute the ImageJ macro (return code: {})".format(return_code)
            nj.job.update(progress=50, statusComment=err_desc)
            raise ValueError(err_desc)

        # 4. Upload the annotation and labels to Cytomine
        upload_data(problem_cls, nj, in_images, out_path, **nj.flags, is_2d=is_2d, monitor_params={
           "start": 60, "end": 90, "period": 0.1
        })

        # 5. Compute and upload the metrics
        nj.job.update(progress=90, statusComment="Computing and uploading metrics...")
        upload_metrics(problem_cls, nj, in_images, gt_path, out_path, tmp_path, **nj.flags)
        
        # 6. End
        nj.job.update(status=Job.TERMINATED, progress=100, statusComment="Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])

