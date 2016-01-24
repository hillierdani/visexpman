#TODO: reis data

import os,shutil,time,logging,datetime,filecmp
transient_backup_path='/mnt/databig/backup'
tape_path='/mnt/tape/hillier/invivocortex/TwoPhoton/new'
mdrive='/mnt/mdrive/invivo/rc'
logfile_path='/mnt/datafast/log/backup_manager.txt'
rei_data='/mnt/databig/debug/cacone'
rei_data_tape=os.path.join(tape_path,'retina')

def is_mounted():
    if not os.path.ismount('/mnt/tape'):
        import subprocess#Mount tape if not mounted
        try:
            subprocess.call(u'mount /mnt/tape',shell=True)
            subprocess.call(u'fusermount -u /mnt/tape',shell=True)
        except:
            pass
    return os.path.ismount('/mnt/tape') and os.path.ismount('/mnt/mdrive')
    
def list_all_files(path):
    all_files = []
    for root, dirs, files in os.walk(path):            
            all_files.extend([root + os.sep + file for file in files])
    return all_files
    
def is_file_closed(f):
    now=time.time()
    return now-os.path.getmtime(f)>600# and now-os.path.getctime(f)>600
    
def copy_file(f):
    try:
        path=f.replace(transient_backup_path+'/','')
        target_path_tape=os.path.join(tape_path,path)
        target_path_m=os.path.join(mdrive,path)
        if os.path.exists(target_path_tape) and filecmp.cmp(f,target_path_tape) and os.path.exists(target_path_m) and filecmp.cmp(f,target_path_m):#Already backed up
            os.remove(f)
            logging.info('Deleted {0}'.format(f))
            return
        for p in [target_path_tape,target_path_m]:
            if not os.path.exists(os.path.dirname(p)):
                os.makedirs(os.path.dirname(p))
        if not is_file_closed(f):
            return
        if not os.path.exists(target_path_tape) or 'mouse' in os.path.basename(target_path_tape):
            shutil.copy2(f,target_path_tape)
            logging.info('Copied to tape: {0}, {1}'.format(f, os.path.getsize(f)))
        if not os.path.exists(target_path_m) or 'mouse' in os.path.basename(target_path_tape):
            shutil.copyfile(f,target_path_m)
            logging.info('Copied to m: {0}, {1}'.format(f, os.path.getsize(f)))
    except:
        import traceback
        logging.error(traceback.format_exc())
        
def rei_backup():
    try:
        files=list_all_files(rei_data)
        phys_files=[f for f in files if '.phys'==f[-5:]]
        coord_files=[f for f in files if 'coords.txt'==os.path.basename(f)]
        rawdata_files=[f for f in files if '.csv'==f[-4:] and 'timestamp' not in os.path.basename(f)]
        backupable_files = phys_files
        backupable_files.extend(coord_files)
        backupable_files.extend(rawdata_files)
        for f in backupable_files:
            target_fn=f.replace(rei_data,rei_data_tape)
            if not os.path.exists(os.path.dirname(target_fn)):
                os.makedirs(os.path.dirname(target_fn))
            if is_file_closed(f) and not os.path.exists(target_fn):
                shutil.copy2(f,target_fn)
                logging.info('Copied {0}'.format(f))
    except:
        import traceback
        logging.error(traceback.format_exc())
    
def run():
    #Check if previous call of backup manager is complete
    with open(logfile_path) as f:
        txt=f.read()
    lines=txt.split('\n')[:-1]
    done_lines = [lines.index(l) for l in lines if 'done' in l]
    started_lines = [lines.index(l) for l in lines if 'listing files' in l]
    if done_lines[-1]<started_lines[-1]:
        ds=[l.split('\t')[0] for l in lines][started_lines[-1]].split(',')[0]
        format="%Y-%m-%d %H:%M:%S"
        if time.time()-time.mktime(datetime.datetime.strptime(ds, format).timetuple())<5*60*60:#If last start happend 3 hours before, assume that there was an error and backup can be started again
            return
        
    logging.basicConfig(filename= logfile_path,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.DEBUG)
    if not is_mounted():
        logging.error('Tape or m mdirve not mounted')
        return
    logging.info('listing files')
    files = list_all_files(transient_backup_path)
    files.sort()
    
    for f in files:
        copy_file(f)
    rei_backup()
    logging.info('done')

if __name__ == "__main__":
    run()