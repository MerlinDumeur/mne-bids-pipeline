"""
===============
06. Evoked data
===============

The evoked data sets are created by averaging different conditions.
"""

import itertools
import logging

import mne
from mne.parallel import parallel_func

from mne_bids import BIDSPath

import config
from config import gen_log_message, on_error, failsafe_run

logger = logging.getLogger('mne-bids-pipeline')


@failsafe_run(on_error=on_error)
def run_evoked(subject, session=None):
    bids_path = BIDSPath(subject=subject,
                         session=session,
                         task=config.get_task(),
                         acquisition=config.acq,
                         run=None,
                         recording=config.rec,
                         space=config.space,
                         extension='.fif',
                         datatype=config.get_datatype(),
                         root=config.deriv_root)

    processing = None
    if config.use_ica or config.use_ssp:
        processing = 'clean'

    fname_in = bids_path.copy().update(processing=processing, suffix='epo',
                                       check=False)
    fname_out = bids_path.copy().update(suffix='ave', check=False)

    msg = f'Input: {fname_in}, Output: {fname_out}'
    logger.info(gen_log_message(message=msg, step=6, subject=subject,
                                session=session))

    epochs = mne.read_epochs(fname_in, preload=True)

    msg = 'Creating evoked data based on experimental conditions …'
    logger.info(gen_log_message(message=msg, step=6, subject=subject,
                                session=session))
    all_evoked = dict()

    if isinstance(config.conditions, dict):
        for new_cond_name, orig_cond_name in config.conditions.items():
            evoked = epochs[orig_cond_name].average()
            evoked.comment = evoked.comment.replace(orig_cond_name,
                                                    new_cond_name)
            all_evoked[new_cond_name] = evoked
    else:
        for condition in config.conditions:
            evoked = epochs[condition].average()
            all_evoked[condition] = evoked

    if config.contrasts:
        msg = 'Contrasting evoked responses …'
        logger.info(gen_log_message(message=msg, step=6, subject=subject,
                                    session=session))

        for contrast in config.contrasts:
            cond_1, cond_2 = contrast
            evoked_diff = mne.combine_evoked([all_evoked[cond_1],
                                              all_evoked[cond_2]],
                                             weights=[1, -1])
            all_evoked[contrast] = evoked_diff

    evokeds = list(all_evoked.values())
    mne.write_evokeds(fname_out, evokeds)

    if config.interactive:
        for evoked in evokeds:
            evoked.plot()

        # What's next needs channel locations
        # ts_args = dict(gfp=True, time_unit='s')
        # topomap_args = dict(time_unit='s')

        # for condition, evoked in zip(config.conditions, evokeds):
        #     evoked.plot_joint(title=condition, ts_args=ts_args,
        #                       topomap_args=topomap_args)


def main():
    """Run evoked."""
    msg = 'Running Step 6: Create evoked data'
    logger.info(gen_log_message(step=6, message=msg))

    parallel, run_func, _ = parallel_func(run_evoked, n_jobs=config.N_JOBS)
    parallel(run_func(subject, session) for subject, session in
             itertools.product(config.get_subjects(), config.get_sessions()))

    msg = 'Completed Step 6: Create evoked data'
    logger.info(gen_log_message(step=6, message=msg))


if __name__ == '__main__':
    main()
