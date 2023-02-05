import React, {useEffect, useState} from 'react'
import './index.css'

import Posts from '../../components/Posts'
import Pagination from '../../components/Pagination'

import * as fakeData from '../../utils/FakeData'


const CardContainer = ({searchQuery}) => {

  //fetch data and send limited data to CardDashboard using the search query
  const dataset =  fakeData.data
  console.log({dataset})

  //const [posts, setPosts] = useState([]);
  const [filteredPosts, setFilteredPosts]= useState([])
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [postsPerPage] = useState(8);

  useEffect(() => {
    const fetchPosts =  () => {
      setLoading(true);
      

      //if search query present update all to be rendered dataset
      if(searchQuery){
        setFilteredPosts(
          dataset.filter((fpost)=>
            fpost.project.toLowerCase().includes(searchQuery.toLowerCase())
          )
        )
      }

      if(!searchQuery){
        setFilteredPosts(()=> [...dataset]);
      }

    };

    fetchPosts();
  }, [searchQuery,dataset]);
  

  //get current posts
  // Get current posts
  const indexOfLastPost = currentPage * postsPerPage;
  const indexOfFirstPost = indexOfLastPost - postsPerPage;
  const currentPosts = filteredPosts.slice(indexOfFirstPost, indexOfLastPost);

  // console.log("indexOfLastPost - "+indexOfLastPost + " indexOfFirstPost = "+indexOfFirstPost+" currentPage "+currentPage)

  // Change page
  const paginate = (pageNumber) => setCurrentPage(pageNumber);



  return (
    <div className='card-container-main'>
        <Posts posts={currentPosts} loading={loading} />
        <div className='pagination-container'>
          <Pagination className=''
            postsPerPage={postsPerPage}
            totalPosts={filteredPosts.length}
            currentPage={currentPage}
            paginate={paginate}
          />
        </div>
        
    </div>
  )
}

export default CardContainer