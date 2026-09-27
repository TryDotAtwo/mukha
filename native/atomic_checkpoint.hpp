#pragma once
#include <cerrno>
#include <cstdio>
#include <filesystem>
#include <stdexcept>
#include <string>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <io.h>
#include <fcntl.h>
#include <sys/stat.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif

// Single-writer protocol: a stale .pending file fails closed. Recovery must
// inspect it explicitly; never silently remove another writer's pending file.
class AtomicCheckpoint {
    std::filesystem::path destination_, temporary_;
    FILE* file_=nullptr;
    bool owns_=false;
public:
    explicit AtomicCheckpoint(const char* path):destination_(path),temporary_(destination_) {
        temporary_ += ".pending";
#ifdef _WIN32
        int fd=_wopen(temporary_.c_str(),_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY,_S_IREAD|_S_IWRITE);
        if(fd<0)throw std::runtime_error("Checkpoint temporary file unavailable");
        file_=_fdopen(fd,"wb");
        if(!file_)_close(fd);
#else
        int fd=open(temporary_.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
        if(fd<0)throw std::runtime_error("Checkpoint temporary file unavailable");
        file_=fdopen(fd,"wb");
        if(!file_)close(fd);
#endif
        owns_=true;
        if(!file_){std::error_code error;std::filesystem::remove(temporary_,error);throw std::runtime_error("Checkpoint stream creation failed");}
    }
    AtomicCheckpoint(const AtomicCheckpoint&)=delete;
    AtomicCheckpoint& operator=(const AtomicCheckpoint&)=delete;
    ~AtomicCheckpoint(){
        if(file_)std::fclose(file_);
        if(owns_){std::error_code error;std::filesystem::remove(temporary_,error);}
    }
    void write(const void* data,size_t size){
        if(std::fwrite(data,1,size,file_)!=size)throw std::runtime_error("Checkpoint write failed");
    }
    void commit(){
        if(std::fflush(file_))throw std::runtime_error("Checkpoint flush failed");
#ifdef _WIN32
        if(_commit(_fileno(file_)))throw std::runtime_error("Checkpoint sync failed");
#else
        if(fsync(fileno(file_)))throw std::runtime_error("Checkpoint sync failed");
#endif
        int result=std::fclose(file_);file_=nullptr;
        if(result)throw std::runtime_error("Checkpoint close failed");
#ifdef _WIN32
        if(!MoveFileExW(temporary_.c_str(),destination_.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))
            throw std::runtime_error("Checkpoint publication failed");
#else
        if(std::rename(temporary_.c_str(),destination_.c_str()))throw std::runtime_error("Checkpoint publication failed");
#endif
        owns_=false;
        // Rename is atomic on supported local filesystems. Directory fsync and
        // storage-specific crash durability remain outside this contract.
    }
};
