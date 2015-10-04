# linking_EC2
Python package for simplifying working with [EC2](https://console.aws.amazon.com/ec2).
Built for automatically uploading [BayesFlow](https://github.com/JonasWallin/BayesFlow).
Warning the program is nowhere near optimal (or safe).

The ipython notebook script/running MPI4py.ipynb shows how to set up a cluster and run a simple mpi4py example.


####TODO:
* parallel the function send_command_ssh
* add: export DEBIAN_FRONTEND=noninteractive
* Add spotprices usage ** , currently there is a incosistency in spot price versus regular reservations!!!, fix it!!
* Add possiblity to turn off closing connection when terminting the object
* Add starting up connection