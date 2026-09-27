//! Process-level atomic checkpoint publication; no power-loss durability claim.
use std::{fs::{self,File,OpenOptions},io::{self,Read,Write},path::{Path,PathBuf}};

struct PendingFile { path:PathBuf,file:Option<File>,owned:bool }
impl PendingFile {
    fn new(destination:&Path)->io::Result<Self> {
        let mut pending=destination.as_os_str().to_os_string();pending.push(".pending");
        let path=PathBuf::from(pending);
        let file=OpenOptions::new().create_new(true).write(true).open(&path)?;
        Ok(Self { path,file:Some(file),owned:true })
    }
    fn commit(mut self,destination:&Path)->io::Result<()> {
        self.file.as_mut().unwrap().flush()?;
        self.file.as_ref().unwrap().sync_all()?;
        drop(self.file.take());
        fs::rename(&self.path,destination)?;
        self.owned=false;
        Ok(())
    }
}
impl Drop for PendingFile {
    fn drop(&mut self) {
        drop(self.file.take());
        if self.owned { let _=fs::remove_file(&self.path); }
    }
}
pub fn write_atomic(destination:&Path,bytes:&[u8])->io::Result<()> {
    let mut pending=PendingFile::new(destination)?;
    pending.file.as_mut().unwrap().write_all(bytes)?;
    pending.commit(destination)
}
pub fn read_exact_size(path:&Path,size:usize)->io::Result<Vec<u8>> {
    let mut file=File::open(path)?;
    if file.metadata()?.len()!=size as u64 {
        return Err(io::Error::new(io::ErrorKind::InvalidData,"Checkpoint file size mismatch"));
    }
    let mut bytes=Vec::new();
    bytes.try_reserve_exact(size).map_err(io::Error::other)?;
    bytes.resize(size,0);
    file.read_exact(&mut bytes)?;
    let mut extra=[0u8;1];
    if file.read(&mut extra)?!=0 {
        return Err(io::Error::new(io::ErrorKind::InvalidData,"Checkpoint grew during read"));
    }
    Ok(bytes)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn publication_preserves_previous_file_and_foreign_pending() {
        let tag=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
        let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("build").join(format!("checkpoint-{}-{tag}",std::process::id()));
        fs::create_dir(&root).unwrap();
        let destination=root.join("снимок.bin");
        let pending=root.join("снимок.bin.pending");
        write_atomic(&destination,b"old").unwrap();
        {
            let mut partial=PendingFile::new(&destination).unwrap();
            partial.file.as_mut().unwrap().write_all(b"unfinished").unwrap();
        }
        assert_eq!(fs::read(&destination).unwrap(),b"old");
        assert!(!pending.exists());
        fs::write(&pending,b"another writer").unwrap();
        assert!(write_atomic(&destination,b"new").is_err());
        assert_eq!(fs::read(&pending).unwrap(),b"another writer");
        assert_eq!(fs::read(&destination).unwrap(),b"old");
        fs::remove_file(&pending).unwrap();
        write_atomic(&destination,b"new data").unwrap();
        assert_eq!(read_exact_size(&destination,8).unwrap(),b"new data");
        assert!(read_exact_size(&destination,7).is_err());
        assert!(!pending.exists());
        let directory=root.join("directory");fs::create_dir(&directory).unwrap();
        assert!(write_atomic(&directory,b"not a directory").is_err());
        assert!(directory.is_dir());assert!(!root.join("directory.pending").exists());
        fs::remove_dir(directory).unwrap();fs::remove_file(destination).unwrap();fs::remove_dir(root).unwrap();
    }
}
