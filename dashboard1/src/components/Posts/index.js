import { Grid } from '@material-ui/core';
import React from 'react';
import CardDashboard from '../../components/CardDashboard'


const Posts = ({ posts, loading }) => {
//   if (loading) {
//     return <h2>Loading...</h2>;
//   }

React.useEffect(()=>{
    console.log({posts})
},[posts]);

  return (
    <Grid container spacing={6}>
      {posts.map((post,index) => (
        <Grid item key={index} xs={12} sm={4} md={3}>
            <CardDashboard badge={post.badge} title={post.title} project={post.project} description= {post.description} lastModified={post.lastModified} owner={post.owner}  />
        </Grid>
         ))}
         </Grid> 
  );
};

export default Posts;