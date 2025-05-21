# ./tmp/assets/config.yamlのパスを変更します。 
# python replace_configyaml.pyを実行してください。
import yaml

with open("./tmp/assets/config.yaml", 'r') as yml:
    config = yaml.safe_load(yml)

config["pipeline"]["params"]["segmentation"] = "./tmp/assets/pytorch_model.bin"

with open("./tmp/assets/config.yaml", 'w') as f:
    yaml.dump(config, f)
