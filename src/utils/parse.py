import os

from utils.attribute_hashmap import AttributeHashmap
from utils.log_util import log


def parse_settings(config: AttributeHashmap, log_settings: bool = True):
    # fix typing issues
    config.learning_rate = float(config.learning_rate)
    config.weight_decay = float(config.weight_decay)

    # fix path issues
    CUTS_ROOT = '/'.join(
        os.path.dirname(os.path.abspath(__file__)).split('/')[:-2])

    config.dataset_path = config.dataset_path.replace('$CUTS_ROOT', CUTS_ROOT)
    config.model_save_path = config.model_save_path.replace(
        '$CUTS_ROOT', CUTS_ROOT)
    config.output_save_path = config.output_save_path.replace(
        '$CUTS_ROOT', CUTS_ROOT)
    config.log_folder = config.log_folder.replace('$CUTS_ROOT', CUTS_ROOT)

    # for ablation test
    if config.model_setting == 'no_recon':
        config.lambda_recon_loss = 0
    if config.model_setting == 'no_contrastive':
        config.lambda_contrastive_loss = 0

    # Initialize log file.
    config.log_dir = config.log_folder + '/' + \
        os.path.basename(
            config.config_file_name).replace('.yaml', '') + '_log.txt'
    if log_settings:
        log_str = 'Config: \n'
        for key in config.keys():
            log_str += '%s: %s\n' % (key, config[key])
        log_str += '\nTraining History:'
        log(log_str, filepath=config.log_dir, to_console=True)
    return config