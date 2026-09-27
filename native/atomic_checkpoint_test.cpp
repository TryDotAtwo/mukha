#include "atomic_checkpoint.hpp"
#include <fstream>
#include <iostream>
#include <iterator>
std::string read(const std::filesystem::path& p){std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
void require(bool good){if(!good)throw std::runtime_error("Atomic checkpoint assertion failed");}
int main(int argc,char** argv){try{
    if(argc!=2)return 2;
    const std::filesystem::path root(argv[1]);
    if(!std::filesystem::create_directory(root))return 3;
    const auto destination=root/"state";
    {AtomicCheckpoint f(destination.string().c_str());f.write("old",3);f.commit();}
    {AtomicCheckpoint f(destination.string().c_str());f.write("partial",7);}
    require(read(destination)=="old" && !std::filesystem::exists(root/"state.pending"));
    {std::ofstream f(root/"state.pending");f<<"other writer";}
    bool rejected=false;
    try{AtomicCheckpoint f(destination.string().c_str());}catch(const std::runtime_error&){rejected=true;}
    require(rejected && read(destination)=="old" && read(root/"state.pending")=="other writer");
    std::filesystem::remove(root/"state.pending");
    {AtomicCheckpoint f(destination.string().c_str());f.write("new",3);require(read(destination)=="old");f.commit();}
    require(read(destination)=="new");
    const auto blocked=root/"blocked";std::filesystem::create_directory(blocked);
    rejected=false;
    try{AtomicCheckpoint f(blocked.string().c_str());f.write("no",2);f.commit();}catch(const std::runtime_error&){rejected=true;}
    require(rejected && std::filesystem::is_directory(blocked) && !std::filesystem::exists(root/"blocked.pending"));
    std::cout<<"PASS: initial publication, abandoned write, writer collision, replacement, failed publication\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
