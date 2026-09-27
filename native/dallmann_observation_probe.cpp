#include "dallmann_observation.h"
#include <iostream>
#include <iomanip>
int main(){
    using namespace dallmann_reference;
    std::cout<<std::setprecision(17);
    std::vector<double> a={90,89,88,86,86,87,89,90,90};
    for(int m=0;m<6;++m){
        auto p=predict(a,5,static_cast<Motion>(m),m==0?-5:5,
            m==4?std::vector<double>{0,0,0,1,0,0,0,0,0}:std::vector<double>{});
        for(std::size_t i=0;i<a.size();++i)
            std::cout<<m<<" "<<i<<" "<<p.activation[i]<<" "<<p.kernel[i]<<" "<<p.calcium[i]<<"\n";
    }
    int rejected=0;
    try{predict({90},5,Motion::club,5);}catch(const std::domain_error&){++rejected;}
    try{predict(a,0,Motion::club,5);}catch(const std::domain_error&){++rejected;}
    try{predict(a,5,static_cast<Motion>(7),5);}catch(const std::domain_error&){++rejected;}
    try{predict(a,5,Motion::nine_a,5);}catch(const std::domain_error&){++rejected;}
    try{predict(a,5,Motion::club,5,{1});}catch(const std::domain_error&){++rejected;}
    std::cout<<"rejected "<<rejected<<"\n";
}
