import React from 'react'

const getData = async(title: string) => {
  console.log("title param",title)
  const response = await fetch(`https://dummyjson.com/posts/search?q=${title}`)
  const data = await response.json()
  return data
}

const BlogTitle = async ({params}) => {
  console.log({params})

  const {title} = params
  const postData = await getData(title);
  console.log({postData})
  const postTitle = postData.posts[0].title
  console.log({postTitle})

  return (
    <div>
      <h1>Blog Title</h1>
      <h5>{postTitle}</h5>
    </div>
    
  )
}

export default BlogTitle