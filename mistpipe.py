#takes in a list of fasta files from spades (maybe quast) and runs blast on them,
# identifying the strains they came from (MLST)

import argparse
import os
import glob
import subprocess
import multiprocessing
import shutil
import csv
import re
import json

def getfasta(path):
    fastalist = []
    for direc in path:
        filelist = glob.glob(os.path.join(direc, '*.fasta'))  # path is a list of directories due to nargs argument
        for file in filelist:
            fastalist.append(file)
    return fastalist


def pathfinder(outpath):
    if not os.access(outpath, os.F_OK):
        os.mkdir(outpath)
    if not os.access(outpath+'temp/', os.F_OK):
        os.mkdir(outpath+'temp/')


def mistargs(mistcall, fastalist, outpath, testtypename, testtype, alleles):
    '''formats arguments for calling MIST. as a list due to mistcall being a list'''
    for file in fastalist:
        strain, extension = os.path.splitext(os.path.basename(file))
        if not os.path.isfile(os.path.join(outpath, strain+testtypename+'.json')):  # make sure not to repeat analyzing a genome
            missed = mistcall + ['-b',
                    '-j', outpath+strain+testtypename+'.json',
                    '-a', alleles,
                    '-t', testtype,
                    '-T', outpath+'temp/'+strain+'/',
                    file]
            yield missed, strain
        else:
            print('skipping strain '+strain+' due to .json file for this test already existing')

def testnamegetter(testtype):
    '''Grabs the name of the test being run from the markers file'''
    with open(testtype, 'r') as f:
        try:
            data = json.load(f)
            for genome, keys in data.items():
                for key in keys:
                    if re.match('T(est)?\.?[-\._ ]?Name.*', key, flags=re.IGNORECASE):
                        return keys[key]

        except ValueError: #if access as .json file fails, try to access as csv file
            f.seek(0)
            reader=csv.reader(f, delimiter='\t')
            next(reader, None)
            for x in reader:
                testname=x[1]
                return testname

def runmist(missed, outpath, strain):
    if not os.access(outpath+'temp/'+strain+'/', os.F_OK):
        os.mkdir(os.path.join(outpath, 'temp/', strain))
    subprocess.call(missed)
    shutil.rmtree(os.path.join(outpath, 'temp', strain+'/'))  # deletes temp folder for MIST which can get big. Not necessary if using the altered version of MIST




def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--outpath', default='./mistout/')
    parser.add_argument('-a', '--alleles', default='alleles/')
    parser.add_argument('-t', '--testtype', required=True, help='path to and type of test/markers file, ex. CGF119')
    parser.add_argument('-c', '--cores', default=multiprocessing.cpu_count(), help='number of cores to run on')
    parser.add_argument('--mistcall', nargs='+', default=['mist'])
    parser.add_argument('path', nargs='+')
    return parser.parse_args()


def process(mistcall, path, outpath, testtype, alleles, cores):
    listlist = getfasta(path)
    testtypename=testnamegetter(testtype)
    pool = multiprocessing.Pool(int(cores))
    pathfinder(outpath)
    margs = mistargs(mistcall, listlist, outpath, testtypename, testtype, alleles)
    for missed, strain in margs:
        pool.apply_async(runmist, args=(missed, outpath, strain))
    pool.close()
    pool.join()


def main():
    args = arguments()
    process(args.mistcall, args.path, args.outpath, args.testtype, args.alleles, args.cores)

if __name__ == '__main__':
    main()