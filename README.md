dict-diagnostic
===============

Latest version of the tools to create Tesserae's Greek-Latin translation 
dictionary, as well as ancillary scripts for testing the output.

working notes
-------------

The lexica themselves aren't in this repo. For the moment, I'm downloading them 
from the Tesserae web site; ultimately they should come from the 
'PerseusDL/lexica' repo on GitHub.

Here's how I'm running these scripts (after `vagrant up`, `vagrant ssh`)

       /vagrant/scripts/read-lexicon.py --match --stem
       /vagrant/scripts/sims-export.py --output /vagrant/results/trans2mws.csv \
            --corpus latin --query greek --results 2 --weight 0.1 

If you want to get things done a little quicker, you can run `sims-export.py`
twice concurrently, for example using `screen`, or just logging into the vm
twice. In that case, do something like this:

       # in one session:
       /vagrant/scripts/sims-export.py --output part_1 --child 1:2 \
            --corpus latin --query greek --results 2 --weight 0.1
        
       # in the other:
       /vagrant/scripts/sims-export.py --output part_2 --child 2:2 \
            --corpus latin --query greek --results 2 --weight 0.1
       
       # put them together:
       cat part_1 part_2 > /vagrant/results/trans2mws.csv

