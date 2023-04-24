import React from 'react'
import AuthForm from '@/components/Authform'
import TestComp from '@/components/TestComp'

// ROUTE : /signin

const SignInHome = () => {
  return (
    <div>
      <AuthForm mode='signin' />
    </div>
  )
}

export default SignInHome