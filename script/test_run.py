## short tutorial on running MPI4py on EC2 

from ConfigParser import ConfigParser
config = ConfigParser()
starfigconfig_folder = "/Users/jonaswallin/.starcluster/"
config.read(starfigconfig_folder + "config")

acess_key_id     = config.get('aws info', 'aws_access_key_id'    , 0)
aws_secret_key   = config.get('aws info', 'aws_secret_access_key', 0)
aws_region_name  = config.get('aws info', 'aws_region_name'      , 0)
my_key_loc       = config.get('key mykeyABC', 'key_location',0)

from linkingEC2 import LinkingHandler
linker = LinkingHandler(aws_secret_access_key = aws_secret_key,
                        aws_access_key_id     = acess_key_id,
                        aws_region_name       = aws_region_name,
                        key_location          = my_key_loc,
                        key_name              = 'mykeyABC' )
linker.start_cluster('ami-d05e75b8', 't2.micro', ['Deafult'],2)

print( linker.get_ssh_login() )

linker.terminate_cluster()